#include<stdio.h>

float square(float num) {
    return num * num;
}

float sum_squares(float x, float y) {
    return square(x) + square(y);
}

int main() {
    printf("%f\n", sum_squares(2, 10));
    return 0;
}