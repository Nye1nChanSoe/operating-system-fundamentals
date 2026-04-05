#ifndef MINER_H
#define MINER_H

#include <stdint.h>
#include <stdio.h>

static inline uint64_t hash(uint64_t x)
{
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9;
    x = (x ^ (x >> 27)) * 0x94d049bb133111eb;
    x = x ^ (x >> 31);
    return x;
}

#define SLICE_SIZE 1000000
#define LOWER_BITS_MASK 0xfffffff

static inline int mine(uint64_t seed, uint64_t base, uint64_t *result)
{
    uint64_t end = base + SLICE_SIZE;

    for (uint64_t i = base; i < end; i++)
    {
        uint64_t hashed = i ^ seed;

        for (int j = 0; j < 10; j++)
        {
            hashed = hash(hashed);
        }

        if ((hashed & LOWER_BITS_MASK) == 0)
        {
            *result = i;
            return 1;
        }
    }

    return 0;
}

#endif