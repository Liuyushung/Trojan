# -*- coding: utf-8 -*-
"""
Created on Sat Jan 11 14:48:24 2020

@author: 劉又聖
"""

def bignum_to_bytes(n):
    result = b''
    while n > 0:
        b = n % 128     # 只取 7 bits
        n >>= 7         # 位移 7 bits, 高位數移下來
        if n:
            b += 128    # 後面還有，位元組高位填 1
        result += bytes([b])    # 小於 256(1 byte) 的數字，可以直接轉成 bytes
    return result

def bytes_to_bignum(bs):
    result, exp = 0, 0
    for b in bs:                # 每次取出為 1 byte, 8 bit
        n = b % 128             # 從 byte 取出其中 7 bits
        result += n << exp      # 先傳的是低位，後面是高位, << 優先於 +=
        exp += 7
        if b & (1 << 7) == 0:   # 最高位是 0 結束
            break
    return result        