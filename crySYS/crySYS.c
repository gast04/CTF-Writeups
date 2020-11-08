#include <stdio.h>
#include <unistd.h>

//gcc -o challenge -no-pie -fno-stack-protector challenges.c
//LD_PRELOAD=./libc-2.27.so ./ld-2.27.so ./challenge

int not_vulnerable() {
  char buf[80];
  return read(0, buf, 0x1000); 
}


int main(){
	not_vulnerable();
    return 0;
}