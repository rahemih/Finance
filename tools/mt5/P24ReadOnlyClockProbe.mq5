// P24ReadOnlyClockProbe.mq5 — S1 local read-only provenance diagnostic.
// NEVER send orders, query identity/credentials, access files, or alter symbol settings.
// Broker tick/server epoch has NOT been attested. Do NOT correct timestamps here.
#property strict
#property script_show_inputs
#property version "1.00"

input string InpSymbol = "EURUSD";

void OnStart()
{
   // Only explicit operator-selected, already visible symbol is read.
   if(StringLen(InpSymbol) < 1 || StringLen(InpSymbol) > 20)
   {
      Print("P24_CLOCK_V1_ERROR|reason=INVALID_SYMBOL");
      return;
   }

   for(int i = 1; i <= 3; i++)
   {
      MqlTick tick;
      ZeroMemory(tick);
      ResetLastError();
      if(!SymbolInfoTick(InpSymbol, tick) || tick.time_msc <= 0)
      {
         PrintFormat("P24_CLOCK_V1_ERROR|reason=NO_TICK|sample=%d|error=%d", i, GetLastError());
         return;
      }

      // Capture raw numeric values. These calls are sequential, not atomic.
      datetime clock_gmt = TimeGMT();
      datetime clock_local = TimeLocal();
      int gmt_offset = TimeGMTOffset();
      datetime last_quote_server = TimeCurrent();
      datetime estimated_trade_server = TimeTradeServer();

      // Fixed, numeric-only privacy-safe schema: no account/server/path/price.
      PrintFormat(
         "P24_CLOCK_V1|sample=%d|symbol=%s|tick_s=%I64d|tick_ms=%I64d|gmt_s=%I64d|local_s=%I64d|gmt_offset_s=%d|server_last_s=%I64d|server_est_s=%I64d|status=OK",
         i, InpSymbol, (long)tick.time, (long)tick.time_msc,
         (long)clock_gmt, (long)clock_local, gmt_offset,
         (long)last_quote_server, (long)estimated_trade_server
      );
      if(i < 3) Sleep(1200);
   }
}
