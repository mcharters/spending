#!/usr/bin/env python3
"""
Helper script to generate password hashes for .env file
Usage: python generate_password.py
"""
from werkzeug.security import generate_password_hash
import getpass

def main():
    print("Password Hash Generator for Spending Tracker")
    print("=" * 50)

    username = input("Enter username: ")
    password = getpass.getpass("Enter password: ")

    # Generate hash
    password_hash = generate_password_hash(password)

    print("\n" + "=" * 50)
    print("Copy this line to your .env file:")
    print(f"AUTH_USER1={username}:{password_hash}")
    print("=" * 50)

if __name__ == '__main__':
    main()
