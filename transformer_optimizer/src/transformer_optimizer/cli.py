import argparse


def main():
    parser = argparse.ArgumentParser(description="Toroidal transformer optimizer")
    parser.add_argument("--version", action="version", version="0.1.0")
    parser.parse_args()
    parser.print_help()


if __name__ == "__main__":
    main()
