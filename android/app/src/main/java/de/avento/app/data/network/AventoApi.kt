package de.avento.app.data.network

import de.avento.app.data.model.Activity
import de.avento.app.data.model.ActivityList
import de.avento.app.data.model.ActivityTrack
import de.avento.app.data.model.ActivityUpdate
import de.avento.app.data.model.BootstrapRequest
import de.avento.app.data.model.CompareRequest
import de.avento.app.data.model.CompareResponse
import de.avento.app.data.model.LoginRequest
import de.avento.app.data.model.OverviewStatistics
import de.avento.app.data.model.PasswordChangeRequest
import de.avento.app.data.model.PasswordResetRequest
import de.avento.app.data.model.Profile
import de.avento.app.data.model.ProfileUpdate
import de.avento.app.data.model.RefreshRequest
import de.avento.app.data.model.RegisterRequest
import de.avento.app.data.model.SummaryResponse
import de.avento.app.data.model.TokenResponse
import de.avento.app.data.model.WeatherResponse
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface AventoApi {
    @POST("auth/bootstrap")
    suspend fun bootstrap(@Body request: BootstrapRequest): TokenResponse

    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): TokenResponse

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): TokenResponse

    @POST("auth/refresh")
    suspend fun refresh(@Body request: RefreshRequest): TokenResponse

    @POST("auth/logout")
    suspend fun logout(@Body request: RefreshRequest): Response<Unit>

    @POST("auth/password-reset")
    suspend fun resetPassword(@Body request: PasswordResetRequest): Response<Unit>

    @GET("profile")
    suspend fun profile(): Profile

    @PATCH("profile")
    suspend fun updateProfile(@Body request: ProfileUpdate): Profile

    @POST("profile/password")
    suspend fun changePassword(@Body request: PasswordChangeRequest): Response<Unit>

    @GET("activities")
    suspend fun activities(
        @Query("limit") limit: Int = 50,
        @Query("offset") offset: Int = 0,
        @Query("q") query: String? = null,
        @Query("type") type: String? = null,
        @Query("date_from") dateFrom: String? = null,
        @Query("date_to") dateTo: String? = null,
    ): ActivityList

    @Multipart
    @POST("activities")
    suspend fun uploadActivity(
        @Part file: MultipartBody.Part,
        @Part("title") title: RequestBody? = null,
        @Part("type") type: RequestBody? = null,
        @Part("notes") notes: RequestBody? = null,
    ): Activity

    @GET("activities/{id}")
    suspend fun activity(@Path("id") id: String): Activity

    @PATCH("activities/{id}")
    suspend fun updateActivity(@Path("id") id: String, @Body request: ActivityUpdate): Activity

    @DELETE("activities/{id}")
    suspend fun deleteActivity(@Path("id") id: String): Response<Unit>

    @GET("activities/{id}/track")
    suspend fun track(@Path("id") id: String): ActivityTrack

    @GET("activities/{id}/weather")
    suspend fun weather(@Path("id") id: String): WeatherResponse

    @POST("activities/{id}/weather/refresh")
    suspend fun refreshWeather(@Path("id") id: String): WeatherResponse

    @GET("activities/{id}/summary")
    suspend fun summary(@Path("id") id: String): SummaryResponse

    @POST("activities/{id}/summary")
    suspend fun generateSummary(
        @Path("id") id: String,
        @Query("force") force: Boolean = false,
    ): SummaryResponse

    @GET("statistics/overview")
    suspend fun statistics(): OverviewStatistics

    @POST("activities/compare")
    suspend fun compare(@Body request: CompareRequest): CompareResponse
}
