// RTSS is 32-bit. NVIDIA's active SDK service requires a 64-bit client.
// Launch only the adjacent local helper; do not create any startup entry.
#include <windows.h>
#include <cwchar>
#include <cstdlib>
static HINSTANCE module=nullptr;
static HANDLE child=nullptr;
static void addFrameViewSdkToPath(){
 const wchar_t* dirs[]={
  L"C:\\Program Files\\NVIDIA Corporation\\FrameViewSDK\\SDK\\Public_Release",
  L"C:\\Program Files (x86)\\NVIDIA Corporation\\FrameViewSDK\\SDK\\Public_Release"
 };
 for(const auto* dir:dirs){
  wchar_t dll[1024];swprintf_s(dll,L"%s\\FvSDK_x64.dll",dir);
  if(GetFileAttributesW(dll)==INVALID_FILE_ATTRIBUTES)continue;
  wchar_t oldPath[32768];DWORD n=GetEnvironmentVariableW(L"PATH",oldPath,32768);
  wchar_t newPath[32768];
  if(n<32768)swprintf_s(newPath,L"%s;%s",dir,n?oldPath:L"");
  else swprintf_s(newPath,L"%s",dir);
  SetEnvironmentVariableW(L"PATH",newPath);
  break;
 }
}
extern "C" __declspec(dllexport) BOOL Start(){
 if(child&&WaitForSingleObject(child,0)==WAIT_TIMEOUT)return TRUE;
 if(child){CloseHandle(child);child=nullptr;}
 wchar_t exe[32768];GetModuleFileNameW(module,exe,32768);
 wchar_t* last=wcsrchr(exe,L'\\');if(!last)return FALSE;
 wcscpy_s(last+1,32768-(last+1-exe),L"FrameViewBridge64.exe");
 STARTUPINFOW startup{};startup.cb=sizeof(startup);PROCESS_INFORMATION proc{};
 wchar_t args[32768];swprintf_s(args,L"\"%s\" --parent %lu",exe,GetCurrentProcessId());
 addFrameViewSdkToPath();
 if(!CreateProcessW(exe,args,nullptr,nullptr,FALSE,CREATE_NO_WINDOW,nullptr,nullptr,&startup,&proc))return FALSE;
 child=proc.hProcess;CloseHandle(proc.hThread);return TRUE;
}
extern "C" __declspec(dllexport) void Stop(){
 HANDLE event=OpenEventW(EVENT_MODIFY_STATE,FALSE,L"Local\\QuietMintFrameViewBridgeStop");
 if(event){SetEvent(event);CloseHandle(event);}
 if(child){WaitForSingleObject(child,3000);CloseHandle(child);child=nullptr;}
}
extern "C" __declspec(dllexport) BOOL Setup(HWND){return FALSE;}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID){
 if(reason==DLL_PROCESS_ATTACH){module=instance;DisableThreadLibraryCalls(instance);}return TRUE;
}
