<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>TIS Cihaz Keşfi - Gerçek Ağ Taraması</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .device-card {
            border-left: 4px solid #28a745;
            transition: all 0.3s ease;
        }
        .device-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .scan-progress {
            display: none;
        }
        .confidence-high { border-left-color: #28a745; }
        .confidence-medium { border-left-color: #ffc107; }
        .confidence-low { border-left-color: #dc3545; }
        .log-container {
            max-height: 400px;
            overflow-y: auto;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
        }
        .target-info {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body class="bg-light">
    <div class="container mt-4">
        <div class="row">
            <div class="col-12">
                <div class="target-info">
                    <h1 class="mb-3">
                        <i class="fas fa-search"></i> TIS Cihaz Keşfi - Gerçek Ağ Taraması
                    </h1>
                    <p class="mb-0">
                        <i class="fas fa-bullseye"></i> Hedef TIS Cihazınız: <strong>192.168.1.200:6000</strong>
                        <br><i class="fas fa-network-wired"></i> Ağınızdaki tüm TIS cihazları taranacak
                    </p>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-cogs"></i> Tarama Ayarları</h5>
                    </div>
                    <div class="card-body">
                        <form id="scanForm">
                            <div class="mb-3">
                                <label class="form-label">
                                    <i class="fas fa-crosshairs"></i> Hedef TIS IP
                                </label>
                                <input type="text" class="form-control" id="specific_ip" value="192.168.1.200" required>
                                <small class="text-muted">Bilinen TIS cihazınızın IP adresi</small>
                            </div>

                            <div class="mb-3">
                                <label class="form-label">
                                    <i class="fas fa-plug"></i> Hedef TIS Port
                                </label>
                                <input type="number" class="form-control" id="specific_port" value="6000" min="1" max="65535" required>
                                <small class="text-muted">TIS cihazınızın port numarası</small>
                            </div>

                            <div class="mb-3">
                                <label class="form-label">
                                    <i class="fas fa-network-wired"></i> Ağ Aralığı
                                </label>
                                <input type="text" class="form-control" id="network_range" value="192.168.1.0/24" required>
                                <small class="text-muted">Taranacak IP aralığı (CIDR formatında)</small>
                            </div>

                            <div class="mb-3">
                                <label class="form-label">
                                    <i class="fas fa-clock"></i> Zaman Aşımı (saniye)
                                </label>
                                <input type="number" class="form-control" id="timeout" value="5" min="1" max="30" required>
                                <small class="text-muted">Her cihaz için bekleme süresi</small>
                            </div>

                            <button type="submit" class="btn btn-primary w-100" id="scanBtn">
                                <i class="fas fa-radar"></i> Gerçek TIS Cihazlarını Tara
                            </button>

                            <div class="scan-progress mt-3" id="scanProgress">
                                <div class="progress mb-2">
                                    <div class="progress-bar progress-bar-striped progress-bar-animated" role="progressbar" style="width: 100%"></div>
                                </div>
                                <small class="text-muted">
                                    <i class="fas fa-spinner fa-spin"></i> Ağ taraması devam ediyor...
                                </small>
                            </div>
                        </form>
                    </div>
                </div>

                <div class="card mt-3">
                    <div class="card-header">
                        <h6><i class="fas fa-info-circle"></i> Tarama Bilgileri</h6>
                    </div>
                    <div class="card-body">
                        <small class="text-muted">
                            <strong>Tarama Stratejisi:</strong><br>
                            1. Önce hedef cihazınız test edilecek<br>
                            2. Sonra tüm ağ taranacak<br>
                            3. Port'lar: 6000, 4001, 4002, 8080<br>
                            4. TIS discovery paketleri gönderilecek
                        </small>
                    </div>
                </div>
            </div>

            <div class="col-md-8">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5><i class="fas fa-list"></i> Bulunan TIS Cihazları</h5>
                        <span class="badge bg-info" id="deviceCount">0 cihaz</span>
                    </div>
                    <div class="card-body">
                        <div id="deviceResults" class="row">
                            <div class="col-12 text-center text-muted py-5">
                                <i class="fas fa-search fa-3x mb-3"></i>
                                <p>Gerçek TIS cihazlarınızı bulmak için tarama başlatın</p>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="card mt-3">
                    <div class="card-header">
                        <h6><i class="fas fa-terminal"></i> Tarama Logları</h6>
                    </div>
                    <div class="card-body">
                        <div id="scanLogs" class="log-container">
                            <div class="text-muted">Tarama logları burada görünecek...</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const scanForm = document.getElementById('scanForm');
            const scanBtn = document.getElementById('scanBtn');
            const scanProgress = document.getElementById('scanProgress');
            const deviceResults = document.getElementById('deviceResults');
            const deviceCount = document.getElementById('deviceCount');
            const scanLogs = document.getElementById('scanLogs');

            // Add initial log
            addLog('🔧 TIS Cihaz Keşif Sistemi Hazır', 'info');
            addLog('🎯 Hedef: 192.168.1.200:6000', 'info');

            scanForm.addEventListener('submit', function(e) {
                e.preventDefault();
                performScan();
            });

            function performScan() {
                const formData = {
                    specific_ip: document.getElementById('specific_ip').value,
                    specific_port: document.getElementById('specific_port').value,
                    network_range: document.getElementById('network_range').value,
                    timeout: document.getElementById('timeout').value,
                    _token: document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                };

                // UI updates
                scanBtn.disabled = true;
                scanBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Taranıyor...';
                scanProgress.style.display = 'block';
                deviceResults.innerHTML = '<div class="col-12 text-center"><i class="fas fa-spinner fa-spin fa-2x"></i><p>Ağ taranıyor...</p></div>';

                // Clear logs and add scan start info
                scanLogs.innerHTML = '';
                addLog('🚀 TIS Ağ Taraması Başlatılıyor...', 'info');
                addLog(`🎯 Hedef: ${formData.specific_ip}:${formData.specific_port}`, 'info');
                addLog(`🌐 Ağ Aralığı: ${formData.network_range}`, 'info');
                addLog(`⏱️ Timeout: ${formData.timeout} saniye`, 'info');

                // Perform scan
                fetch('/api/scan-network', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': formData._token
                    },
                    body: JSON.stringify(formData)
                })
                .then(response => response.json())
                .then(data => {
                    handleScanResults(data);
                })
                .catch(error => {
                    console.error('Scan error:', error);
                    addLog('❌ Tarama hatası: ' + error.message, 'error');
                    resetScanUI();
                });
            }

            function handleScanResults(data) {
                resetScanUI();

                if (data.success && data.devices.length > 0) {
                    addLog(`✅ Tarama tamamlandı: ${data.devices.length} TIS cihazı bulundu!`, 'success');
                    displayDevices(data.devices);
                    deviceCount.textContent = `${data.devices.length} cihaz`;
                    deviceCount.className = 'badge bg-success';

                    // Show scan info
                    if (data.scan_info) {
                        addLog(`📊 Tarama Bilgileri:`, 'info');
                        addLog(`   • Hedef: ${data.scan_info.specific_target}`, 'info');
                        addLog(`   • Ağ: ${data.scan_info.network_range}`, 'info');
                        addLog(`   • Zaman: ${data.scan_info.scan_time}`, 'info');
                    }
                } else {
                    addLog('⚠️ Hiç TIS cihazı bulunamadı', 'warning');
                    deviceResults.innerHTML = `
                        <div class="col-12 text-center text-warning py-5">
                            <i class="fas fa-exclamation-triangle fa-3x mb-3"></i>
                            <h5>TIS Cihazı Bulunamadı</h5>
                            <p>Lütfen ağ ayarlarınızı kontrol edin:</p>
                            <ul class="list-unstyled">
                                <li>• TIS cihazının çalıştığından emin olun</li>
                                <li>• IP adresi doğru mu? (${document.getElementById('specific_ip').value})</li>
                                <li>• Port doğru mu? (${document.getElementById('specific_port').value})</li>
                                <li>• Aynı ağda mı?</li>
                                <li>• Firewall engelliyor mu?</li>
                            </ul>
                        </div>
                    `;
                    deviceCount.textContent = '0 cihaz';
                    deviceCount.className = 'badge bg-warning';
                }

                if (data.message) {
                    addLog('📝 ' + data.message, data.success ? 'success' : 'error');
                }
            }

            function displayDevices(devices) {
                let html = '';

                devices.forEach((device, index) => {
                    const confidenceClass = `confidence-${device.confidence || 'medium'}`;
                    const confidenceBadge = getConfidenceBadge(device.confidence);
                    
                    html += `
                        <div class="col-md-6 mb-3">
                            <div class="card device-card ${confidenceClass}">
                                <div class="card-body">
                                    <div class="d-flex justify-content-between align-items-start mb-2">
                                        <h6 class="card-title mb-0">
                                            <i class="fas fa-microchip"></i> ${device.device_name}
                                        </h6>
                                        ${confidenceBadge}
                                    </div>
                                    
                                    <div class="mb-2">
                                        <small class="text-muted">
                                            <i class="fas fa-network-wired"></i> 
                                            <strong>${device.ip}:${device.port}</strong>
                                        </small>
                                    </div>
                                    
                                    <div class="mb-2">
                                        <small class="text-muted">
                                            <i class="fas fa-tag"></i> Tip: ${device.device_type}
                                        </small>
                                        <br>
                                        <small class="text-muted">
                                            <i class="fas fa-fingerprint"></i> ID: ${device.device_id}
                                        </small>
                                    </div>

                                    ${device.response && device.response !== 'connected_no_response' ? 
                                        `<div class="mb-2">
                                            <small class="text-muted">
                                                <i class="fas fa-exchange-alt"></i> Yanıt: 
                                                <code>${device.response.substring(0, 20)}...</code>
                                            </small>
                                        </div>` : ''
                                    }
                                    
                                    <div class="d-flex justify-content-between align-items-center">
                                        <small class="text-muted">
                                            <i class="fas fa-clock"></i> ${device.last_seen}
                                        </small>
                                        <span class="badge bg-success">
                                            <i class="fas fa-circle"></i> Online
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });

                // Add action buttons
                html += `
                    <div class="col-12 mt-3">
                        <div class="d-flex gap-2">
                            <button class="btn btn-success" onclick="addAllDevices()">
                                <i class="fas fa-plus-circle"></i> Tüm Cihazları Sisteme Ekle
                            </button>
                            <button class="btn btn-outline-info" onclick="exportDevices()">
                                <i class="fas fa-download"></i> JSON Export
                            </button>
                        </div>
                    </div>
                `;

                deviceResults.innerHTML = html;
            }

            function getConfidenceBadge(confidence) {
                const badges = {
                    'high': '<span class="badge bg-success">Yüksek Güven</span>',
                    'medium': '<span class="badge bg-warning">Orta Güven</span>', 
                    'low': '<span class="badge bg-danger">Düşük Güven</span>'
                };
                return badges[confidence] || badges['medium'];
            }

            function resetScanUI() {
                scanBtn.disabled = false;
                scanBtn.innerHTML = '<i class="fas fa-radar"></i> Gerçek TIS Cihazlarını Tara';
                scanProgress.style.display = 'none';
            }

            function addLog(message, type = 'info') {
                const timestamp = new Date().toLocaleTimeString('tr-TR');
                const typeColors = {
                    'info': 'text-info',
                    'success': 'text-success', 
                    'warning': 'text-warning',
                    'error': 'text-danger'
                };

                const logEntry = document.createElement('div');
                logEntry.className = `mb-1 ${typeColors[type] || 'text-muted'}`;
                logEntry.innerHTML = `[${timestamp}] ${message}`;
                
                scanLogs.appendChild(logEntry);
                scanLogs.scrollTop = scanLogs.scrollHeight;
            }

            // Global functions for buttons
            window.addAllDevices = function() {
                // This would add all discovered devices to the system
                addLog('🚀 Tüm cihazlar sisteme ekleniyor...', 'info');
                // Implementation would go here
            };

            window.exportDevices = function() {
                // Export devices as JSON
                addLog('📄 Cihaz listesi JSON olarak export ediliyor...', 'info');
                // Implementation would go here  
            };
        });
    </script>
</body>
</html>