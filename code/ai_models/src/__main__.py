from src.api import create_app
from src.config import load_settings


def main() -> None:
    settings = load_settings()
    create_app(settings).run(host=settings.host, port=settings.port, debug=False)


if __name__ == "__main__":
    main()
