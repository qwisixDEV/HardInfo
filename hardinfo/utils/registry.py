"""Windows Registry backup and restore management.
"""

import os
import json
import logging
import winreg
from hardinfo.constants import REGISTRY_BACKUP_FILE


class SafeRegistryBackup:
    @staticmethod
    def load_backup():
        if os.path.exists(REGISTRY_BACKUP_FILE):
            try:
                with open(REGISTRY_BACKUP_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def save_backup(data):
        try:
            with open(REGISTRY_BACKUP_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"[ERROR] Ошибка бэкапа реестра: {e}")

    @classmethod
    def backup_value(cls, hive_name, path, value_name, expected_type=winreg.REG_DWORD):
        backup_data = cls.load_backup()
        key_str = f"{hive_name}\\{path}\\{value_name}"
        if key_str in backup_data:
            return

        hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
        original_val = None
        original_type = expected_type

        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                original_val, original_type = winreg.QueryValueEx(key, value_name)
        except FileNotFoundError:
            original_val = "__missing__"
        except Exception as e:
            logging.warning(f"[SYSTEM] Пропущено резервирование {key_str}: {e}")
            return

        backup_data[key_str] = {
            "hive": hive_name,
            "path": path,
            "value_name": value_name,
            "value": original_val,
            "type": original_type
        }
        cls.save_backup(backup_data)
        logging.info(f"[SYSTEM] Создан бэкап: {key_str} -> {original_val}")

    @classmethod
    def restore_all(cls):
        backup_data = cls.load_backup()
        if not backup_data:
            return True, "Нет сохраненных резервных копий."

        success_count = 0
        failed_count = 0
        for key_str, item in backup_data.items():
            hive_name = item["hive"]
            path = item["path"]
            value_name = item["value_name"]
            orig_val = item["value"]
            orig_type = item["type"]

            hive = winreg.HKEY_CURRENT_USER if hive_name == "HKCU" else winreg.HKEY_LOCAL_MACHINE
            try:
                if orig_val == "__missing__":
                    try:
                        with winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE) as key:
                            winreg.DeleteValue(key, value_name)
                        success_count += 1
                    except FileNotFoundError:
                        success_count += 1
                else:
                    try:
                        key = winreg.CreateKeyEx(hive, path, 0, winreg.KEY_SET_VALUE)
                    except Exception:
                        key = winreg.OpenKey(hive, path, 0, winreg.KEY_SET_VALUE)
                    with key:
                        winreg.SetValueEx(key, value_name, 0, orig_type, orig_val)
                    success_count += 1
            except Exception as e:
                logging.error(f"[ERROR] Не удалось восстановить {key_str}: {e}")
                failed_count += 1

        if failed_count == 0:
            return True, f"Все твики реестра ({success_count}) возвращены по умолчанию."
        return False, f"Восстановлено: {success_count}. Сбоев: {failed_count}."
