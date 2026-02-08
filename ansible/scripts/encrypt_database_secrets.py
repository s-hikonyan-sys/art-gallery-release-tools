#!/usr/bin/env python3
"""secrets.yaml.encryptedファイルを作成するスクリプト.

Ansible Vaultで暗号化されたvault-config.yaml.vaultからdatabase.passwordを取得し、
Fernetで暗号化してsecrets.yaml.encryptedを作成します。"""

import sys
from pathlib import Path

# Ansibleディレクトリ内からファイルを特定
# __file__ = ansible/scripts/encrypt_database_secrets.py
# parent.parent = ansible ディレクトリ
ansible_dir = Path(__file__).parent.parent
db_secrets_path = ansible_dir / "roles" / "database" / "files" / "secrets.py"

import yaml

# SecretManagerをインポート
# config/__init__.pyをインポートするとConfigクラスが実行時にconfig.yamlを読み込もうとするため、
# データベースロール内に配置した secrets.py を直接インポートする
import importlib.util
spec = importlib.util.spec_from_file_location(
    "secrets",
    db_secrets_path
)
secrets_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(secrets_module)
SecretManager = secrets_module.SecretManager


def main():
    """メイン処理."""
    if len(sys.argv) < 4:
        print("Usage: encrypt_secrets.py <vault_file> <secret_key> <output_file>", file=sys.stderr)
        sys.exit(1)
    
    vault_file = Path(sys.argv[1])
    secret_key = sys.argv[2]
    output_file = Path(sys.argv[3])
    
    # Ansible Vaultで復号化（ansible-vaultコマンドを使用）
    import subprocess
    try:
        # .vault_passファイルを探す（playbook_dir/.vault_pass）
        playbook_dir = Path(__file__).parent.parent
        vault_pass_file = playbook_dir / ".vault_pass"
        
        if not vault_pass_file.exists():
            print(f"Error: .vault_pass not found at {vault_pass_file}", file=sys.stderr)
            sys.exit(1)
        
        result = subprocess.run(
            ["ansible-vault", "decrypt", "--output", "-", "--vault-password-file", str(vault_pass_file), str(vault_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        vault_data = yaml.safe_load(result.stdout) or {}
    except subprocess.CalledProcessError as e:
        print(f"Error decrypting vault file: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: ansible-vault not found. Please install ansible-core.", file=sys.stderr)
        sys.exit(1)
    
    # database.passwordを取得
    db_password = vault_data.get("database", {}).get("password", "")
    if not db_password:
        print("Error: database.password not found in vault file", file=sys.stderr)
        sys.exit(1)
    
    # Fernetで暗号化
    secret_manager = SecretManager(secret_key=secret_key)
    encrypted_password = secret_manager.encrypt(db_password)
    
    # secrets.yaml.encryptedを作成
    secrets_data = {
        "database": {
            "password": f"encrypted:{encrypted_password}"
        }
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.dump(secrets_data, f, default_flow_style=False, allow_unicode=True)
    
    print(f"✓ Created {output_file}")


if __name__ == "__main__":
    main()
