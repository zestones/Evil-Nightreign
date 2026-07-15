#include "stdafx.h"
extern int Kraken_Decompress(const byte *src, size_t src_len, byte *dst, size_t dst_len);
extern "C" int ooz_decompress(const uint8_t *src, size_t src_len, uint8_t *dst, size_t dst_len) {
  return Kraken_Decompress(src, src_len, dst, dst_len);
}
