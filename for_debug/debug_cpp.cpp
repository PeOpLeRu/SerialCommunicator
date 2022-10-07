#include <iostream>

using namespace std;
/*
int CRC_hash(const uint8_t* data, const int size)
{
    int hash = 0;
    for (int i = 0; i < size; ++i)
    {
        unsigned int highorder = hash & 0xf8000000;
        hash = hash << 5;
        hash = hash ^ (highorder >> 27);
        hash = hash ^ data[i];
    }

    return hash;
}
*/

int CRC_hash(const uint8_t* data, const int size)
{
    int hash = 0;
    unsigned int highorder = 0;

    for (int i = 0; i < size; ++i)
    {
        highorder = hash & 0xf8000000;
        hash = hash << 5;
        hash = hash ^ (highorder >> 27);
        hash = hash ^ data[i];
    }

    return hash;
}

int main()
{
    uint8_t data[] = { 3,   1,   1,   0,   0,   0,   0,   0,   0,   0,   0,   0,   0,
 };
    int hash = CRC_hash(data, 13);
    cout << ((hash >> 24) & 0xFF) << ", " << ((hash >> 16) & 0xFF) << ", " << ((hash >> 8) & 0xFF) << ", " << (hash & 0xFF);
}