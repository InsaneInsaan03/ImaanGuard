import win32serviceutil
import win32service
import win32event
import servicemanager
import os
import sys
import logging
import threading

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [Service]: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), "..", "data", "service.log")),
        logging.StreamHandler()
    ]
)

class ImaanGuardService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ImaanGuardService"
    _svc_display_name_ = "ImaanGuard Protection Service"
    _svc_description_ = "Monitors system activity and enforces lockdown mechanism."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = False

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.is_running = False
        win32event.SetEvent(self.stop_event)
        logging.info("ImaanGuard service stopping")

    def SvcDoRun(self):
        self.is_running = True
        self.ReportServiceStatus(win32service.SERVICE_START_PENDING)  # Report pending status
        logging.info("ImaanGuard service starting")

        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, "")
        )

        def run_main():
            try:
                main_script = os.path.join(os.path.dirname(__file__), "main.py")
                os.chdir(os.path.dirname(__file__))
                self.ReportServiceStatus(win32service.SERVICE_RUNNING)  # Report running status
                import main
                main.main()
            except Exception as e:
                logging.error(f"Service error: {e}")
                servicemanager.LogErrorMsg(str(e))
                self.SvcStop()

        # Start the main logic in a separate thread
        thread = threading.Thread(target=run_main)
        thread.start()

        # Wait for stop event
        win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
        logging.info("ImaanGuard service stopped")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ImaanGuardService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ImaanGuardService)