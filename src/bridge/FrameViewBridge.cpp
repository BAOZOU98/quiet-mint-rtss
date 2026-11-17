// Local RTSS client plugin. Reads the installed NVIDIA FrameView SDK only.
// Publishes SDK averages through RTSS's existing AIDA64 sensor provider.
// No network, input injection, game modifications, or additional startup entry.
#include <windows.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "FvSDK.h"
#include "RTSSSharedMemory.h"
// The SDK static wrapper resolves its versioned query interface internally.
// Missing vendor runtimes are reported by FvSDK_Initialize, not direct exports.
static bool disableSdk=false;
static HANDLE stopEvent=nullptr, worker=nullptr;
static HMODULE module=nullptr;
static volatile LONG status=0;
// RTSS 7.3.7 clears application entries when the server restarts, while a
// game already hooked can keep using its old slot. Recover only that slot's
// missing position and subsequent saved-position edits. Never rewrite profiles.
static void recoverPosition(){
 struct Recovered { DWORD pid=0; LONG x=0,y=0; };
 static Recovered recovered[256];
 HANDLE mapping=OpenFileMappingW(FILE_MAP_ALL_ACCESS,FALSE,L"RTSSSharedMemoryV2");
 if(!mapping)return;
 auto mem=static_cast<RTSS_SHARED_MEMORY*>(MapViewOfFile(mapping,FILE_MAP_ALL_ACCESS,0,0,0));
 if(mem){
  DWORD index=mem->dwLastForegroundApp,pid=mem->dwLastForegroundAppProcessID;
  if(mem->dwSignature=='RTSS'&&mem->dwVersion>=0x20010&&pid&&index<mem->dwAppArrSize&&index<256){
   auto entry=reinterpret_cast<RTSS_SHARED_MEMORY::RTSS_SHARED_MEMORY_APP_ENTRY*>(reinterpret_cast<BYTE*>(mem)+mem->dwAppArrOffset+index*mem->dwAppEntrySize);
   if(!entry->dwProcessID){
    HANDLE process=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,pid);
    char exe[32768];DWORD size=sizeof(exe);
    bool gotPath=process&&QueryFullProcessImageNameA(process,0,exe,&size);
    if(!gotPath){if(process)CloseHandle(process);UnmapViewOfFile(mem);CloseHandle(mapping);return;}
    {
     char root[32768];GetModuleFileNameA(nullptr,root,sizeof(root));
     char* plugin=strrchr(root,'\\');
     if(plugin){
      *plugin=0;plugin=strrchr(root,'\\');if(plugin)*plugin=0;
      plugin=strrchr(root,'\\');if(plugin)*plugin=0;
      char global[32768],profile[32768];
      sprintf_s(global,"%s\\Profiles\\Global",root);
      const char* base=strrchr(exe,'\\');base=base?base+1:exe;
      sprintf_s(profile,"%s\\Profiles\\%s.cfg",root,base);
      LONG x=GetPrivateProfileIntA("OSD","PositionX",1,global);
      LONG y=GetPrivateProfileIntA("OSD","PositionY",1,global);
      if(gotPath){x=GetPrivateProfileIntA("OSD","PositionX",x,profile);y=GetPrivateProfileIntA("OSD","PositionY",y,profile);}
      // The slot and foreground PID can change while configuration is read.
      auto& prior=recovered[index];
      bool changed=prior.pid!=pid||prior.x!=x||prior.y!=y;
      if(changed&&mem->dwLastForegroundApp==index&&mem->dwLastForegroundAppProcessID==pid&&!entry->dwProcessID){
       entry->dwOSDX=static_cast<DWORD>(x);entry->dwOSDY=static_cast<DWORD>(y);
       InterlockedIncrement(reinterpret_cast<volatile LONG*>(&mem->dwOSDFrame));
       prior.pid=pid;prior.x=x;prior.y=y;
      }
     }
    }
    if(process)CloseHandle(process);
   }
  }
  UnmapViewOfFile(mem);
 }
 CloseHandle(mapping);
}
static DWORD gamePid(){
 DWORD pid=0;
 HANDLE map=OpenFileMappingW(FILE_MAP_READ,FALSE,L"RTSSSharedMemoryV2");
 if(map){
  auto mem=static_cast<const RTSS_SHARED_MEMORY*>(MapViewOfFile(map,FILE_MAP_READ,0,0,0));
  if(mem){
   if(mem->dwSignature=='RTSS'&&mem->dwVersion>=0x00020010) pid=mem->dwLastForegroundAppProcessID;
   UnmapViewOfFile(mem);
  }
  CloseHandle(map);
 }
 return pid;
}
static void publish(char* memory,double pcl,double render,double low=-1){
 char xml[1024];
 SYSTEMTIME localTime{};GetLocalTime(&localTime);
 char p[32]="N/A",r[32]="N/A",l[32]="N/A";
 if(std::isfinite(pcl)&&pcl>0&&pcl<10000) sprintf_s(p,"%.3f",pcl);
 if(std::isfinite(render)&&render>0&&render<10000) sprintf_s(r,"%.3f",render);
 if(std::isfinite(low)&&low>0&&low<100000) sprintf_s(l,"%.3f",low);
 sprintf_s(xml,"<sys><id>NV_PCL_AV</id><label>FrameView PC latency average</label><value>%s</value></sys>"
 "<sys><id>NV_RLAT</id><label>FrameView render present latency</label><value>%s</value></sys>"
 "<sys><id>NV_FPS_LOW</id><label>FrameView FPS one percent low</label><value>%s</value></sys>"
 "<sys><id>LOCAL_HOUR</id><label>Local hour</label><value>%u</value></sys>"
 "<sys><id>LOCAL_MINUTE</id><label>Local minute</label><value>%u</value></sys>",p,r,l,localTime.wHour,localTime.wMinute);
 memcpy(memory,xml,strlen(xml)+1);
}
static double readMetric(FvSession session,FvMetricType type,DWORD pid){
 Samples samples;samples.type=type;
 auto result=FvSDK_ReadData(session,&samples,1);
 if((result!=FV_SUCCESS&&result!=FV_MORE_DATA&&result!=FV_INSUFFICIENT_BUFFER)||!samples.mNumSamples||samples.mNumSamples>10000) return -1;
 std::vector<AvgSWPCLatency> values(samples.mNumSamples);
 samples.mData=values.data();
 if(FvSDK_ReadData(session,&samples,1)!=FV_SUCCESS) return -1;
 double value=-1;
 for(size_t i=0;i<samples.mNumSamples;i++)
  if(values[i].mFPS.PID==pid) value=values[i].mFPS.AvgFPS;
 return value;
}
static DWORD WINAPI run(void*){
 HMODULE held=nullptr;
#ifndef BRIDGE_EXE
 GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS,reinterpret_cast<LPCWSTR>(&run),&held);
#endif
 HANDLE mapping=CreateFileMappingW(INVALID_HANDLE_VALUE,nullptr,PAGE_READWRITE,0,65536,L"AIDA64_SensorValues");
 // Never overwrite a real AIDA64 instance or another owner's sensor mapping.
 bool owned=mapping&&GetLastError()!=ERROR_ALREADY_EXISTS;
 char* memory=owned?static_cast<char*>(MapViewOfFile(mapping,FILE_MAP_WRITE|FILE_MAP_READ,0,0,65536)):nullptr;
 FvSession session{};
 bool initialized=false,created=false;
 if(memory){
  publish(memory,-1,-1);
  bool sdkAvailable=!disableSdk;
  auto initResult=sdkAvailable?FvSDK_Initialize():FV_ERROR;status=0x10000|initResult;
  initialized=sdkAvailable&&initResult==FV_SUCCESS;
  if(initialized){
   while(WaitForSingleObject(stopEvent,0)==WAIT_TIMEOUT){
    publish(memory,-1,-1);
    auto cr=FvSDK_CreateSession(&session);status=0x20000|cr;created=cr==FV_SUCCESS;
    if(created||WaitForSingleObject(stopEvent,2000)!=WAIT_TIMEOUT)break;
   }
  }
  if(created){
   FvMetricType metrics[]={eAvgSWPCLatency,eRenderPresentLatency,eFPSLow};
   auto enabled=FvSDK_EnableMetrics(session,metrics,3);
   auto started=enabled==FV_SUCCESS?FvSDK_StartSession(session):FV_ERROR;
   status=0x30000|started;
   if(started==FV_SUCCESS||started==FV_SDK_SESSION_IN_PROGRESS){
    while(WaitForSingleObject(stopEvent,500)==WAIT_TIMEOUT){
     DWORD pid=gamePid();
     // FrameView collection is shared with NVIDIA Overlay. Recover if another
     // SDK client stopped collection; do not stop it when this reader exits.
     auto sampled=FvSDK_SampleData(session,FVSDK_SAMPLEDATA_DONOTWAIT);
     if(sampled==FV_SDK_SESSION_NOT_STARTED)FvSDK_StartSession(session);
     if(sampled==FV_SUCCESS||sampled==FV_MORE_DATA){
      publish(memory,readMetric(session,eAvgSWPCLatency,pid),readMetric(session,eRenderPresentLatency,pid),readMetric(session,eFPSLow,pid));
     }else publish(memory,-1,-1);
    }
   }
  }
  while(WaitForSingleObject(stopEvent,500)==WAIT_TIMEOUT)publish(memory,-1,-1);
 }
 if(created)FvSDK_DestroySession(session);
 if(initialized) FvSDK_Shutdown();

 if(memory)UnmapViewOfFile(memory);
 if(mapping)CloseHandle(mapping);
 if(held)FreeLibraryAndExitThread(held,0);
 return 0;
}
extern "C" __declspec(dllexport) BOOL Start(){
 if(worker)return TRUE;
 stopEvent=CreateEventW(nullptr,TRUE,FALSE,nullptr);
 if(!stopEvent)return FALSE;
 worker=CreateThread(nullptr,0,run,nullptr,0,nullptr);
 if(!worker){CloseHandle(stopEvent);stopEvent=nullptr;return FALSE;}
 return TRUE;
}
extern "C" __declspec(dllexport) void Stop(){
 if(stopEvent)SetEvent(stopEvent);
 if(worker&&WaitForSingleObject(worker,3000)==WAIT_OBJECT_0){
  CloseHandle(worker);worker=nullptr;CloseHandle(stopEvent);stopEvent=nullptr;
 }
}
extern "C" __declspec(dllexport) BOOL Setup(HWND){return FALSE;}
extern "C" __declspec(dllexport) LONG Status(){return status;}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID){
 if(reason==DLL_PROCESS_ATTACH){module=instance;DisableThreadLibraryCalls(instance);}
 return TRUE;
}
#ifdef BRIDGE_EXE
int main(int argc,char** argv){
 for(int i=1;i<argc;i++)if(!strcmp(argv[i],"--no-sdk"))disableSdk=true;
 HANDLE mutex=CreateMutexW(nullptr,FALSE,L"Local\\QuietMintFrameViewBridge64");
 if(!mutex||GetLastError()==ERROR_ALREADY_EXISTS){if(mutex)CloseHandle(mutex);return 0;}
 stopEvent=CreateEventW(nullptr,TRUE,FALSE,L"Local\\QuietMintFrameViewBridgeStop");
 if(!stopEvent){CloseHandle(mutex);return 1;}
 ResetEvent(stopEvent);
 HANDLE positionWorker=CreateThread(nullptr,0,[](void*)->DWORD{
  while(WaitForSingleObject(stopEvent,250)==WAIT_TIMEOUT)recoverPosition();
  return 0;
 },nullptr,0,nullptr);
 HANDLE parent=nullptr,watcher=nullptr;
 if(argc==3&&!strcmp(argv[1],"--parent")){
  parent=OpenProcess(SYNCHRONIZE,FALSE,strtoul(argv[2],nullptr,10));
  if(!parent){CloseHandle(stopEvent);CloseHandle(mutex);return 0;}
  watcher=CreateThread(nullptr,0,[](void* process)->DWORD{
   HANDLE events[]={static_cast<HANDLE>(process),stopEvent};
   WaitForMultipleObjects(2,events,FALSE,INFINITE);SetEvent(stopEvent);return 0;
  },parent,0,nullptr);
 }
 run(nullptr);
 if(positionWorker){WaitForSingleObject(positionWorker,2000);CloseHandle(positionWorker);}
 if(watcher){WaitForSingleObject(watcher,2000);CloseHandle(watcher);}
 if(parent)CloseHandle(parent);
 CloseHandle(stopEvent);CloseHandle(mutex);return 0;
}
#endif
