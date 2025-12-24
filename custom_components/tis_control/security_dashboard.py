from __future__ import annotations
from TISControlProtocol import *
import os
from ruamel.yaml import YAML
import logging

#------ Security Settings Setup
def create():
    current_dir = os.path.dirname(__file__)
    base_dir = os.path.abspath(os.path.join(current_dir, alpha__("Li4vLi4v")))
    config_path = os.path.join(base_dir, alpha__("Y29uZmlndXJhdGlvbi55YW1s"))
    dashboard_filename = alpha__("c2VjdXJpdHlfbG9ja19zZXR0aW5ncy55YW1s")
    dashboard_path = os.path.join(base_dir, dashboard_filename)
    try:
        # YAML setup
        yaml = YAML()
        yaml.preserve_quotes = True

        # 1. Load configuration.yaml
        with open(config_path, alpha__("cg==")) as f:
            config = yaml.load(f)

        # 2. Add dashboard if missing
        if alpha__("bG92ZWxhY2U=") not in config:
            config[alpha__("bG92ZWxhY2U=")] = {}
        if alpha__("ZGFzaGJvYXJkcw==") not in config[alpha__("bG92ZWxhY2U=")]:
            config[alpha__("bG92ZWxhY2U=")][alpha__("ZGFzaGJvYXJkcw==")] = {}

        if alpha__("c2VjdXJpdHktbG9jay1zZXR0aW5ncw==") not in config[alpha__("bG92ZWxhY2U=")][alpha__("ZGFzaGJvYXJkcw==")]:
            config[alpha__("bG92ZWxhY2U=")][alpha__("ZGFzaGJvYXJkcw==")][alpha__("c2VjdXJpdHktbG9jay1zZXR0aW5ncw==")] = {
                alpha__("bW9kZQ=="): alpha__("eWFtbA=="),
                alpha__("dGl0bGU="): alpha__("U2VjdXJpdHkgTG9jayBTZXR0aW5ncw=="),
                alpha__("aWNvbg=="): alpha__("bWRpOmxvY2s="),
                alpha__("c2hvd19pbl9zaWRlYmFy"): True,
                alpha__("ZmlsZW5hbWU="): dashboard_filename
            }


        # 3. Save configuration.yaml
        with open(config_path, alpha__("dw==")) as f:
            yaml.dump(config, f)

        # 4. Create dashboard file if not exists
        if not os.path.exists(dashboard_path):
            dashboard_content = {
                alpha__("dGl0bGU="): alpha__("WUFNTCBEYXNoYm9hcmQ="),
                alpha__("dmlld3M="): [
                    {
                        alpha__("dGl0bGU="): alpha__("U2V0dGluZ3M="),
                        alpha__("cGF0aA=="): alpha__("bWFpbg=="),
                        alpha__("Y2FyZHM="): [
                            {
                                alpha__("dHlwZQ=="): alpha__("YnV0dG9u"),
                                alpha__("bmFtZQ=="): alpha__("Q2hhbmdlIFBhc3N3b3Jk"),
                                alpha__("aWNvbg=="): alpha__("bWRpOmxvY2s="),
                                alpha__("dGFwX2FjdGlvbg=="): {
                                    alpha__("YWN0aW9u"): alpha__("dXJs"),
                                    alpha__("dXJsX3BhdGg="): alpha__("aHR0cDovL2hvbWVhc3Npc3RhbnQubG9jYWw6ODAwMC9hcGkvY2hhbmdlLXBhc3N3b3Jk")
                                }
                            }
                        ]
                    }
                ]
            }
            with open(dashboard_path, alpha__("dw==")) as f:
                yaml.dump(dashboard_content, f)
    except Exception as e:
        logging.error(beta__("Q291bGQgTm90IFNldHVwIFNlY3VyaXR5IFNldHRpbmdzIERhc2hib2FyZDoge19fdmFyMH0=", __var0=e))
