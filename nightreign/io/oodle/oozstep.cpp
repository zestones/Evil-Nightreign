#include "stdafx.h"
typedef struct KrakenDecoder KrakenDecoder;
extern KrakenDecoder *Kraken_Create();
extern void Kraken_Destroy(KrakenDecoder*);
extern bool Kraken_DecodeStep(KrakenDecoder*, byte*, int, size_t, const byte*, size_t);
// src_used/dst_used sont les 2 premiers int de la struct
extern "C" int ooz_step(const uint8_t *src, size_t src_len, uint8_t *dst, size_t dst_len,
                        int *out_src_used, int *out_dst_used) {
  KrakenDecoder *d = Kraken_Create();
  bool ok = Kraken_DecodeStep(d, dst, 0, dst_len, src, src_len);
  int *iu = (int*)d; // src_used, dst_used en tête de struct
  *out_src_used = iu[0]; *out_dst_used = iu[1];
  Kraken_Destroy(d);
  return ok ? 1 : 0;
}
