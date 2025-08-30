package au.st1cky.smsautoframe.net

import android.content.Context
import au.st1cky.smsautoframe.util.Prefs
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Query

data class ReplyRequest(val incoming: String, val contact: String? = null)
data class Analysis(
    val sentiment: String? = null,
    val intent: String? = null,
    val toxicity: Int? = null,
    val urgent: Int? = null,
    val boundary_triggers: List<String>? = null
)
data class ReplyResponse(
    val draft: String? = null,
    val reply: String? = null,
    val analysis: Analysis? = null,
    val goal: String? = null,
    val variant: String? = null
)

data class MemoryItemsResponse(
    val contact: String? = null,
    val items: List<Map<String, Any>>? = null
)

data class MemorySummaryResponse(
    val contact: String? = null,
    val summary: String? = null,
    val goal_counts: Map<String, Int>? = null
)

data class GenericOk(val ok: Boolean? = null, val error: String? = null)

data class FeedbackRequest(
    val ts: String,
    val incoming: String,
    val contact: String,
    val draft: String,
    val final: String,
    val accepted: Boolean,
    val edited: Boolean,
    val tags: Map<String, String>? = null
)
data class FeedbackResponse(val ok: Boolean? = null, val status: String? = null)

interface ReplyApi {
    @POST("/reply") suspend fun reply(@Body req: ReplyRequest): ReplyResponse
    @POST("/feedback") suspend fun feedback(@Body req: FeedbackRequest): FeedbackResponse
    @GET("/memory") suspend fun memory(@Query("contact") contact: String, @Query("limit") limit: Int = 5): MemoryItemsResponse
    @GET("/memory/summary") suspend fun memorySummary(@Query("contact") contact: String, @Query("limit") limit: Int = 10): MemorySummaryResponse
    @DELETE("/memory") suspend fun deleteMemory(@Query("contact") contact: String): GenericOk
    @POST("/license/activate") suspend fun activate(@Body body: Map<String, String>): GenericOk
    @GET("/license/status") suspend fun licenseStatus(): Map<String, Any>
    @GET("/license/hwid") suspend fun hwid(): Map<String, String>
}

class ReplyClient private constructor(ctx: Context) {
    private val api: ReplyApi by lazy {
        val retrofit = Retrofit.Builder()
        .baseUrl(Prefs(ctx).serverBase())
        .client(OkHttpClient.Builder().build())
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        retrofit.create(ReplyApi::class.java)
    }

    suspend fun getDraft(incoming: String, contact: String): String {
        val res = api.reply(ReplyRequest(incoming = incoming, contact = contact))
        return (res.draft ?: res.reply ?: "").trim()
    }

    suspend fun getDraftWithMeta(incoming: String, contact: String): ReplyResponse {
        return api.reply(ReplyRequest(incoming = incoming, contact = contact))
    }

    suspend fun sendFeedback(fb: FeedbackRequest): FeedbackResponse = api.feedback(fb)

    suspend fun getMemory(contact: String, limit: Int = 5): MemoryItemsResponse = api.memory(contact, limit)
    suspend fun getMemorySummary(contact: String, limit: Int = 10): MemorySummaryResponse = api.memorySummary(contact, limit)
    suspend fun purgeMemory(contact: String): GenericOk = api.deleteMemory(contact)
    suspend fun activateLicense(token: String): GenericOk = api.activate(mapOf("key" to token))
    suspend fun getLicenseStatus(): Map<String, Any> = api.licenseStatus()
    suspend fun getHardwareId(): String = api.hwid()["hardware_id"] ?: ""

    companion object { fun instance(ctx: Context) = ReplyClient(ctx) }
}
