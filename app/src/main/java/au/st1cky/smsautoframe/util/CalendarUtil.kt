package au.st1cky.smsautoframe.util

import android.content.Context
import android.content.Intent
import android.provider.CalendarContract
import java.util.*

object CalendarUtil {
    fun insertEventIntent(
        ctx: Context,
        title: String,
        startMillis: Long,
        endMillis: Long,
        description: String = ""
    ) {
        val intent = Intent(Intent.ACTION_INSERT).apply {
            data = CalendarContract.Events.CONTENT_URI
            putExtra(CalendarContract.Events.TITLE, title)
            putExtra(CalendarContract.Events.DESCRIPTION, description)
            putExtra(CalendarContract.EXTRA_EVENT_BEGIN_TIME, startMillis)
            putExtra(CalendarContract.EXTRA_EVENT_END_TIME, endMillis)
        }
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        ctx.startActivity(intent)
    }
}
