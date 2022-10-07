#include <iostream>

using namespace std;

int CRC_hash(const uint8_t* data, const int size)
{
  int hash = 0;
  for (int i = 0; i < size; ++i)
  {
    int highorder = hash & 0xf8000000;
    hash = hash << 5;
    hash = hash ^ (highorder >> 27);
    hash = hash ^ data[i];
  } 

  return hash;
}

int main()
[
    uint8_t data[] = { 3, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0 };
    cout << CRC_hash(data, 13);
]