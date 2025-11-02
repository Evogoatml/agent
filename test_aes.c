#include <openssl/evp.h>
#include <stdio.h>
int main() {
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL);
    printf("AES ready\n");
    EVP_CIPHER_CTX_free(ctx);
    return 0;
}
