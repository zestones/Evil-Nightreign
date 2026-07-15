#include "stdafx.h"
struct LznaState; struct BitknitState;
// Ces codecs n'apparaissent jamais dans le DCX FromSoft (Kraken only).
int LZNA_DecodeQuantum(uint8*,uint8*,uint8*,const uint8*,const uint8*,LznaState*){return -1;}
void LZNA_InitLookup(LznaState*){}
int Bitknit_Decode(const uint8*,const uint8*,uint8*,uint8*,uint8*,BitknitState*){return -1;}
void BitknitState_Init(BitknitState*){}
