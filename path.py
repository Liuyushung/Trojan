# -*- coding: utf-8 -*-
"""
Created on Mon Jan 20 12:30:41 2020

@author: 劉又聖
"""

import os
#import stat
#from common import *

# path.py
def split_path(path):
    result = []
    while True:
        head, tail = os.path.split(path)
        if tail:
            result.insert(0, tail)
            path = head
        else:
            head = head.strip('/:\\')
            if head:    result.insert(0, head)
            break
    return result