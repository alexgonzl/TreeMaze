#!/usr/bin/python3

x = input('a number = ')

print('<'.encode())
for ch in x:
    print(ch.encode())
print('>'.encode())
