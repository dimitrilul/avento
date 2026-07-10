package de.avento.app.data.security

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import java.nio.ByteBuffer
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

data class AuthTokens(val accessToken: String, val refreshToken: String)

interface TokenStore {
    val tokens: Flow<AuthTokens?>
    suspend fun read(): AuthTokens?
    suspend fun save(accessToken: String, refreshToken: String)
    suspend fun clear()
}

private val Context.sessionDataStore by preferencesDataStore(name = "secure_session")

class EncryptedTokenStore(private val context: Context) : TokenStore {
    private val cipher = KeystoreCipher()

    override val tokens: Flow<AuthTokens?> = context.sessionDataStore.data.map { preferences ->
        val encryptedAccess = preferences[ACCESS_TOKEN] ?: return@map null
        val encryptedRefresh = preferences[REFRESH_TOKEN] ?: return@map null
        runCatching {
            AuthTokens(
                accessToken = cipher.decrypt(encryptedAccess),
                refreshToken = cipher.decrypt(encryptedRefresh),
            )
        }.getOrNull()
    }

    override suspend fun read(): AuthTokens? = tokens.first()

    override suspend fun save(accessToken: String, refreshToken: String) {
        val encryptedAccess = cipher.encrypt(accessToken)
        val encryptedRefresh = cipher.encrypt(refreshToken)
        context.sessionDataStore.edit { preferences ->
            preferences[ACCESS_TOKEN] = encryptedAccess
            preferences[REFRESH_TOKEN] = encryptedRefresh
        }
    }

    override suspend fun clear() {
        context.sessionDataStore.edit { it.clear() }
    }

    private companion object {
        val ACCESS_TOKEN = stringPreferencesKey("access_token_v1")
        val REFRESH_TOKEN = stringPreferencesKey("refresh_token_v1")
    }
}

private class KeystoreCipher {
    private val key: SecretKey
        get() {
            val keyStore = KeyStore.getInstance(KEYSTORE).apply { load(null) }
            (keyStore.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
            return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE).run {
                init(
                    KeyGenParameterSpec.Builder(
                        KEY_ALIAS,
                        KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
                    )
                        .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                        .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                        .setRandomizedEncryptionRequired(true)
                        .build(),
                )
                generateKey()
            }
        }

    fun encrypt(plainText: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION).apply {
            init(Cipher.ENCRYPT_MODE, key)
        }
        val encrypted = cipher.doFinal(plainText.toByteArray(Charsets.UTF_8))
        val packed = ByteBuffer.allocate(Int.SIZE_BYTES + cipher.iv.size + encrypted.size)
            .putInt(cipher.iv.size)
            .put(cipher.iv)
            .put(encrypted)
            .array()
        return Base64.encodeToString(packed, Base64.NO_WRAP)
    }

    fun decrypt(value: String): String {
        val packed = ByteBuffer.wrap(Base64.decode(value, Base64.NO_WRAP))
        val ivSize = packed.int
        require(ivSize in 12..32) { "Ungültige Token-Verschlüsselung" }
        val iv = ByteArray(ivSize).also(packed::get)
        val encrypted = ByteArray(packed.remaining()).also(packed::get)
        val plainText = Cipher.getInstance(TRANSFORMATION).run {
            init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, iv))
            doFinal(encrypted)
        }
        return plainText.toString(Charsets.UTF_8)
    }

    private companion object {
        const val KEYSTORE = "AndroidKeyStore"
        const val KEY_ALIAS = "avento_session_aes_v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
    }
}
