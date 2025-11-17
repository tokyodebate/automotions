from .app import AutoMotionsApp
from .interface import TUIInterface

def main():
    app = AutoMotionsApp(TUIInterface())
    app.run()

if __name__ == "__main__":
    main()