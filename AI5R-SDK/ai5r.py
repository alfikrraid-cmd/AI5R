#!/usr/bin/env python3

import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ai5r.py <command>")
        print("Available commands: build")
        sys.exit(1)

    command = sys.argv[1]

    if command == "build":
        print("AI5R SDK Compiler")
        print("Build command detected")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
