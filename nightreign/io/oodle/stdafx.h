// Portable (Linux/gcc) replacement for ooz's Windows-only stdafx.h.
#pragma once
#define _CRT_SECURE_NO_WARNINGS 1
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <stdint.h>
#include <x86intrin.h>

typedef unsigned char byte;
typedef unsigned char uint8;
typedef unsigned int uint32;
typedef uint64_t uint64;
typedef int64_t int64;
typedef signed int int32;
typedef unsigned short uint16;
typedef signed short int16;
typedef unsigned int uint;

static inline unsigned char _BitScanReverse(unsigned long *index, unsigned int mask) {
  if (!mask) return 0; *index = 31 - __builtin_clz(mask); return 1;
}
static inline unsigned char _BitScanForward(unsigned long *index, unsigned int mask) {
  if (!mask) return 0; *index = __builtin_ctz(mask); return 1;
}
#define _byteswap_ushort(x) __builtin_bswap16(x)
#define _byteswap_ulong(x)  __builtin_bswap32(x)
#define _byteswap_uint(x)   __builtin_bswap32(x)
#define __debugbreak()      __builtin_trap()
#define __forceinline inline __attribute__((always_inline))
#define _byteswap_uint64(x) __builtin_bswap64(x)
