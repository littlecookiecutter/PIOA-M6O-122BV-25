from .tui import DatabaseApp


def main() -> None:
    app = DatabaseApp()
    app.run()


if __name__ == "__main__":
    main()
