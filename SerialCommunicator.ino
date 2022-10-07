#define SIZE_BUFER 30

void setup()
{
  for (int i = 2; i < 14; ++i)
  {
    pinMode(i, OUTPUT);
  }
  Serial.begin(9600);
  digitalWrite(3, LOW);
  digitalWrite(4, HIGH);
}

uint8_t size_recieve_data_for_commands[] = { 6, 6, 7, 17 };
uint8_t data[SIZE_BUFER];
int lenght_message;

void loop()
{
  while (true)
  {
    if (Serial.available())
    {
      lenght_message = Serial.readBytes(data, SIZE_BUFER);

      if (lenght_message != size_recieve_data_for_commands[data[0]])
      {
        delay(200);
        Serial.readBytes(data, SIZE_BUFER);
        data[0] = 1;
        Serial.write(data, 1);
        continue;
      }

     uint32_t hash = CRC_hash(data, lenght_message - 4);

      bool is_correct_hash = true;
      for (int i = lenght_message - 4, it = 3; i < lenght_message; ++i, it--)
      {
        if (data[i] != ((hash >> (it * 8)) & 0xFF))
        {
          is_correct_hash = false;
          break;
        }
      }

      if (!is_correct_hash)
      { 
        data[0] = 2;
        Serial.write(data, 1);
        continue; 
      }

      input_handler(data[0], data, lenght_message);

      if (lenght_message)
      {
        int hash = CRC_hash(data, lenght_message);

        for (int i = lenght_message, it = 3; i < lenght_message + 4; ++i, it--)
        {
            data[i] = ((hash >> (it * 8)) & 0xFF);
        }
            
        Serial.write(data, lenght_message + 4);
      }
    } 
  }
}

void input_handler(const int cmd_num, uint8_t* data, int& size)
{
  if (cmd_num == 0)
  {
    data[0] = (digitalRead(data[1]) & 0xFF);
    size = 1;
  } 
  else if (cmd_num == 1)
  {
    uint8_t pin = data[1];
    data[0] =  (analogRead(pin) >> 8) & 0xFF;
    data[1] =  analogRead(pin) & 0xFF;
    size = 2;
  }
  else if (cmd_num == 2)
  {
    digitalWrite(data[1], bool(data[2]) ? HIGH : LOW);
    data[0] = 0;    
    Serial.write(data, 1);
    size = 0;
  }
  else if (cmd_num == 3)
  {
    for (int i = 1; i < 13; ++i)
    {
      digitalWrite(i + 1, bool(data[i]) ? HIGH : LOW);
    }
    data[0] = 0;
    Serial.write(data, 1);
    size = 0;
  }

  return;
}

int32_t CRC_hash(const uint8_t* data, const int size)
{
  int32_t hash = 0;
  uint32_t highorder = 0;
  
  for (int i = 0; i < size; ++i)
  {
    highorder = hash & 0xf8000000;
    hash = hash << 5;
    hash = hash ^ (highorder >> 27);
    hash = hash ^ data[i];
  } 

  return hash;
}