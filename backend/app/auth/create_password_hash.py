from getpass import getpass

from app.auth.security import hash_password


def main() -> None:
    password = getpass("Mật khẩu admin ban đầu (ít nhất 8 ký tự): ")
    if len(password) < 8:
        raise SystemExit("Mật khẩu phải có ít nhất 8 ký tự.")
    if password != getpass("Nhập lại mật khẩu: "):
        raise SystemExit("Mật khẩu nhập lại không khớp.")
    print(hash_password(password))


if __name__ == "__main__":
    main()
