package au.st1cky.smsautoframe.net

data class ExtractEventRequest(val text: String, val contact: String)
data class ExtractedEvent(
    val has_event: Boolean,
    val title: String? = null,
    val start_epoch_ms: Long? = null,
    val end_epoch_ms: Long? = null,
    val description: String? = null
)
