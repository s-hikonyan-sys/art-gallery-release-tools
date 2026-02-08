"""機密情報の暗号化・復号化モジュール.

設定ファイル内の機密情報を暗号化して保存し、実行時に復号化します。"""

import base64
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecretManager:
    """機密情報の暗号化・復号化管理クラス.

    secret_key（config.yaml）を使用して、設定ファイル内の機密情報を暗号化・復号化します。"""

    def __init__(self, secret_key: Optional[str] = None):
        """初期化.

        Args:
            secret_key: 暗号化キー（config.yamlのsecret_key）
                          - 指定された場合はそれを使用
                          - 指定されない場合はデフォルト値を使用（本番環境では非推奨）"""
        if not secret_key:
            # Development fallback only - production should use a proper secret key
            secret_key = "default-secret-key-change-in-production"  # nosec B105
        self.secret_key = secret_key
        self._cipher = self._create_cipher()

    def _create_cipher(self) -> Fernet:
        """secret_keyから暗号化キーを生成."""
        # secret_keyから32バイトのキーを生成
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"art_gallery_salt",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode()))
        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """平文を暗号化.

        Args:
            plaintext: 平文

        Returns:
            暗号化された文字列（Base64エンコード）"""
        if not plaintext:
            return ""
        encrypted = self._cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt(self, ciphertext: str) -> str:
        """暗号化された文字列を復号化.

        Args:
            ciphertext: 暗号化された文字列（Base64エンコード）

        Returns:
            復号化された文字列"""
        if not ciphertext:
            return ""
        try:
            decoded = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self._cipher.decrypt(decoded)
            return decrypted.decode()
        except Exception:
            # 復号化に失敗した場合は、平文として扱う（後方互換性）
            return ciphertext

    @staticmethod
    def is_encrypted(value: str) -> bool:
        """値が暗号化されているかどうかを判定.

        Args:
            value: チェックする値

        Returns:
            暗号化されている場合True"""
        return value.startswith("encrypted:") if value else False

    @staticmethod
    def extract_encrypted_value(value: str) -> str:
        """暗号化された値から実際の暗号文を抽出.

        Args:
            value: `encrypted:...`形式の値

        Returns:
            暗号文"""
        if value.startswith("encrypted:"):
            return value[10:]  # 'encrypted:'を除去
        return value
