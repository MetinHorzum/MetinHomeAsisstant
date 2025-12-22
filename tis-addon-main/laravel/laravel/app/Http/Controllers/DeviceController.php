<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use App\Models\Device;
use App\Models\DeviceType;
use App\Models\Appliance;
use App\Models\ApplianceType;

class DeviceController extends Controller
{
    /**
     * Show the device scanner interface
     */
    public function showScanner()
    {
        return view('device-scanner');
    }

    /**
     * Perform network scan for TIS devices
     */
    public function scanNetwork(Request $request)
    {
        try {
            $networkRange = $request->input('network_range', '192.168.1.0/24');
            $timeout = (int)$request->input('timeout', 5);
            $specificIp = $request->input('specific_ip', '192.168.1.200');
            $specificPort = (int)$request->input('specific_port', 6000);

            Log::info("🔍 TIS Ağ Taraması Başlatılıyor", [
                'network_range' => $networkRange,
                'timeout' => $timeout,
                'specific_target' => "$specificIp:$specificPort"
            ]);

            // First test the known TIS device
            $discoveredDevices = [];
            $specificDevice = $this->testSpecificDevice($specificIp, $specificPort, $timeout);
            if ($specificDevice) {
                $discoveredDevices[] = $specificDevice;
                Log::info("✅ Bilinen TIS cihazı bulundu: $specificIp:$specificPort");
            }

            // Then scan the network
            $networkDevices = $this->discoverTISDevices($networkRange, $timeout, $specificPort);
            $discoveredDevices = array_merge($discoveredDevices, $networkDevices);

            // Remove duplicates
            $uniqueDevices = [];
            foreach ($discoveredDevices as $device) {
                $key = $device['ip'] . ':' . $device['port'];
                if (!isset($uniqueDevices[$key])) {
                    $uniqueDevices[$key] = $device;
                }
            }

            $finalDevices = array_values($uniqueDevices);
            $deviceCount = count($finalDevices);

            Log::info("📊 Tarama tamamlandı", [
                'total_found' => $deviceCount,
                'devices' => $finalDevices
            ]);

            return response()->json([
                'success' => true,
                'message' => "$deviceCount TIS cihazı bulundu",
                'devices' => $finalDevices,
                'scan_info' => [
                    'network_range' => $networkRange,
                    'timeout' => $timeout,
                    'specific_target' => "$specificIp:$specificPort",
                    'scan_time' => now()->format('Y-m-d H:i:s')
                ]
            ]);

        } catch (\Exception $e) {
            Log::error("Ağ tarama hatası: " . $e->getMessage());
            
            return response()->json([
                'success' => false,
                'message' => 'Ağ taraması sırasında hata oluştu: ' . $e->getMessage(),
                'devices' => [],
                'error_details' => $e->getTraceAsString()
            ], 500);
        }
    }

    /**
     * Test specific known TIS device
     */
    private function testSpecificDevice($ip, $port, $timeout)
    {
        try {
            Log::info("🎯 Hedef TIS cihazı test ediliyor: $ip:$port");

            // Socket connection test
            $socket = @socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
            if (!$socket) {
                return null;
            }

            socket_set_option($socket, SOL_SOCKET, SO_RCVTIMEO, ['sec' => $timeout, 'usec' => 0]);
            socket_set_option($socket, SOL_SOCKET, SO_SNDTIMEO, ['sec' => $timeout, 'usec' => 0]);

            $result = @socket_connect($socket, $ip, $port);
            
            if ($result) {
                Log::info("✅ Socket bağlantısı başarılı: $ip:$port");

                // Try to send TIS discovery packet
                $tisPacket = pack('C*', 0x55, 0xAA, 0x00, 0x01, 0x00, 0x00, 0x01);
                $sent = @socket_write($socket, $tisPacket);

                $response = '';
                if ($sent) {
                    $response = @socket_read($socket, 1024, PHP_BINARY_READ);
                    if ($response) {
                        $responseHex = bin2hex($response);
                        Log::info("📦 TIS yanıtı alındı: " . $responseHex);
                    }
                }

                socket_close($socket);

                return [
                    'ip' => $ip,
                    'port' => $port,
                    'device_name' => "TIS Cihazı ($ip)",
                    'device_type' => 'TIS-UNKNOWN',
                    'device_id' => $this->extractDeviceId($response ?: ''),
                    'status' => 'online',
                    'response' => $response ? bin2hex($response) : 'connected_no_response',
                    'last_seen' => now()->format('Y-m-d H:i:s'),
                    'confidence' => $response ? 'high' : 'medium'
                ];
            }

            socket_close($socket);

        } catch (\Exception $e) {
            Log::debug("Cihaz test hatası $ip:$port: " . $e->getMessage());
        }

        return null;
    }

    /**
     * Discover TIS devices on network
     */
    private function discoverTISDevices($networkRange, $timeout, $primaryPort)
    {
        $devices = [];

        try {
            // Parse network range
            if (strpos($networkRange, '/') !== false) {
                [$networkBase, $cidr] = explode('/', $networkRange);
                $networkBase = substr($networkBase, 0, strrpos($networkBase, '.'));
            } else {
                $networkBase = substr($networkRange, 0, strrpos($networkRange, '.'));
            }

            // TIS ports to scan (prioritize user's port)
            $tisPorts = [$primaryPort, 4001, 4002, 6000, 6001, 8080, 9090];
            $tisPorts = array_unique($tisPorts); // Remove duplicates

            Log::info("🌐 Ağ tarama başlıyor", [
                'network_base' => $networkBase,
                'ports' => $tisPorts,
                'timeout' => $timeout
            ]);

            // Scan IP range (optimize for faster scanning)
            $scanStart = microtime(true);
            
            for ($i = 1; $i <= 254; $i++) {
                $ip = "$networkBase.$i";

                // Quick ping test first
                if (!$this->isHostReachable($ip, 1)) {
                    continue;
                }

                // Test TIS ports
                foreach ($tisPorts as $port) {
                    $socket = @socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
                    if (!$socket) continue;

                    socket_set_option($socket, SOL_SOCKET, SO_RCVTIMEO, ['sec' => 1, 'usec' => 0]);
                    socket_set_option($socket, SOL_SOCKET, SO_SNDTIMEO, ['sec' => 1, 'usec' => 0]);

                    $result = @socket_connect($socket, $ip, $port);

                    if ($result) {
                        Log::info("🎯 Potansiyel TIS cihazı bulundu: $ip:$port");

                        $devices[] = [
                            'ip' => $ip,
                            'port' => $port,
                            'device_name' => "TIS Cihazı ($ip)",
                            'device_type' => 'TIS-DISCOVERED',
                            'device_id' => 'AUTO-' . strtoupper(dechex(crc32($ip . $port))),
                            'status' => 'online',
                            'response' => 'port_scan_success',
                            'last_seen' => now()->format('Y-m-d H:i:s'),
                            'confidence' => 'medium'
                        ];

                        socket_close($socket);
                        break; // One port per IP is enough for discovery
                    }

                    socket_close($socket);
                }
            }

            $scanDuration = round(microtime(true) - $scanStart, 2);
            Log::info("📊 Ağ taraması tamamlandı", [
                'duration' => $scanDuration . 's',
                'devices_found' => count($devices)
            ]);

        } catch (\Exception $e) {
            Log::error("Network discovery hatası: " . $e->getMessage());
        }

        return $devices;
    }

    /**
     * Quick host reachability check
     */
    private function isHostReachable($ip, $timeout = 1)
    {
        // Simple socket test for reachability
        $socket = @socket_create(AF_INET, SOCK_STREAM, SOL_TCP);
        if (!$socket) return false;

        socket_set_option($socket, SOL_SOCKET, SO_RCVTIMEO, ['sec' => $timeout, 'usec' => 0]);
        socket_set_option($socket, SOL_SOCKET, SO_SNDTIMEO, ['sec' => $timeout, 'usec' => 0]);

        // Try common ports to check if host is alive
        $commonPorts = [80, 443, 22, 21, 23];
        foreach ($commonPorts as $port) {
            $result = @socket_connect($socket, $ip, $port);
            if ($result) {
                socket_close($socket);
                return true;
            }
        }

        socket_close($socket);
        return false;
    }

    /**
     * Extract device ID from TIS response
     */
    private function extractDeviceId($response)
    {
        if (empty($response)) {
            return 'UNKNOWN';
        }

        // Simple device ID extraction (customize based on your TIS protocol)
        $hex = bin2hex($response);
        
        // Look for common TIS device ID patterns
        if (strlen($hex) >= 8) {
            return strtoupper(substr($hex, 0, 4));
        }

        return 'AUTO-' . strtoupper(substr(md5($response), 0, 4));
    }

    /**
     * Add discovered devices to system
     */
    public function addDiscoveredDevices(Request $request)
    {
        try {
            $devices = $request->input('devices', []);
            $addedCount = 0;

            foreach ($devices as $deviceData) {
                $added = $this->addDeviceAutomatically($deviceData);
                if ($added) {
                    $addedCount++;
                }
            }

            Log::info("Cihaz ekleme tamamlandı", [
                'total_devices' => count($devices),
                'added_count' => $addedCount
            ]);

            return response()->json([
                'success' => true,
                'message' => "$addedCount cihaz başarıyla eklendi",
                'added_count' => $addedCount,
                'total_count' => count($devices)
            ]);

        } catch (\Exception $e) {
            Log::error("Cihaz ekleme hatası: " . $e->getMessage());
            
            return response()->json([
                'success' => false,
                'message' => 'Cihaz ekleme sırasında hata oluştu: ' . $e->getMessage()
            ], 500);
        }
    }

    /**
     * Automatically add device to system
     */
    private function addDeviceAutomatically($deviceData)
    {
        try {
            // Check if device already exists
            $existingDevice = Device::where('ip_address', $deviceData['ip'])
                ->where('port', $deviceData['port'])
                ->first();

            if ($existingDevice) {
                Log::info("Cihaz zaten mevcut: " . $deviceData['ip'] . ':' . $deviceData['port']);
                return false;
            }

            // Create device type if not exists
            $deviceType = DeviceType::firstOrCreate([
                'name' => $deviceData['device_type']
            ], [
                'description' => 'Otomatik keşfedilen TIS cihazı',
                'is_active' => true
            ]);

            // Create device
            $device = Device::create([
                'device_name' => $deviceData['device_name'],
                'ip_address' => $deviceData['ip'],
                'port' => $deviceData['port'],
                'device_type_id' => $deviceType->id,
                'device_id' => $deviceData['device_id'],
                'status' => 'active',
                'last_seen' => now(),
                'discovery_method' => 'network_scan',
                'confidence_level' => $deviceData['confidence'] ?? 'medium'
            ]);

            // Create default appliances based on device type
            $this->createDefaultAppliances($device, $deviceData);

            Log::info("Yeni cihaz eklendi", [
                'device_id' => $device->id,
                'name' => $device->device_name,
                'ip' => $device->ip_address,
                'port' => $device->port
            ]);

            return true;

        } catch (\Exception $e) {
            Log::error("Otomatik cihaz ekleme hatası: " . $e->getMessage(), [
                'device_data' => $deviceData
            ]);
            return false;
        }
    }

    /**
     * Create default appliances for discovered device
     */
    private function createDefaultAppliances($device, $deviceData)
    {
        try {
            // Create common appliance types
            $applianceTypes = [
                'light_dimmer' => 'Dimmer Işık',
                'switch_relay' => 'Röle Anahtarı',
                'temperature_sensor' => 'Sıcaklık Sensörü',
                'motion_sensor' => 'Hareket Sensörü'
            ];

            foreach ($applianceTypes as $typeKey => $typeName) {
                $applianceType = ApplianceType::firstOrCreate([
                    'name' => $typeKey
                ], [
                    'display_name' => $typeName,
                    'description' => "Otomatik oluşturulan $typeName",
                    'is_active' => true
                ]);

                // Create sample appliance
                Appliance::create([
                    'device_id' => $device->id,
                    'appliance_type_id' => $applianceType->id,
                    'appliance_name' => $device->device_name . ' - ' . $typeName,
                    'channel' => rand(1, 4), // Random channel
                    'status' => 'active',
                    'auto_created' => true
                ]);
            }

            Log::info("Varsayılan appliance'lar oluşturuldu", [
                'device_id' => $device->id,
                'appliance_count' => count($applianceTypes)
            ]);

        } catch (\Exception $e) {
            Log::error("Varsayılan appliance oluşturma hatası: " . $e->getMessage());
        }
    }
}