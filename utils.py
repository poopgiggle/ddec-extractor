def bit_at_index(byte,index):
    return 1 if byte & (1 << index) else 0#start counting from the right, because DDEC
