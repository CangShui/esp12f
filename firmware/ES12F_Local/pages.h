/*
 * ES12F 本地化固件 —— 内嵌网页
 *  PAGE_CONFIG : 配网页面（与原固件 0x5015C 处的页面逐字节相同）
 *  PAGE_INDEX  : 新增的电源控制页面
 * 所有页面放在 PROGMEM（Flash）里，不占用 RAM。
 */
#ifndef ES12F_PAGES_H
#define ES12F_PAGES_H

/* ===== 1. 配网页面：与原固件完全一致的原始页面 ===== */
static const char PAGE_CONFIG[] PROGMEM = R"rawliteral(<!DOCTYPE html>
<html lang='en'>
<head>
  <title>WIFI 配网</title>
  <meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0, user-scalable=no, minimum-scale=1.0, maximum-scale=1.0'/>
  <style type='text/css'>
  .login-page {
  width: 360px;
  padding: 8% 0 0;
  margin: auto;}
.form {
  position: relative;
  z-index: 1;
  background: #FFFFFF;
  max-width: 360px;
  margin: 0 auto 100px;
  padding: 45px;
  text-align: center;
  box-shadow: 0 0 20px 0 rgba(0, 0, 0, 0.2), 0 5px 5px 0 rgba(0, 0, 0, 0.24);}
.form input, .form select {
  font-family: 'Roboto', sans-serif;
  outline: 0;
  background: #f2f2f2;
  width: 100%;
  border: 0;
  margin: 0 0 15px;
  padding: 15px;
  box-sizing: border-box;
  font-size: 14px;}
.form button {
  font-family: 'Roboto', sans-serif;
  text-transform: uppercase;
  outline: 0;
  background: #4CAF50;
  width: 100%;
  border: 0;
  padding: 15px;
  color: #FFFFFF;
  font-size: 14px;
  -webkit-transition: all 0.3 ease;
  transition: all 0.3 ease;
  cursor: pointer;}
.form button:hover,.form button:active,.form button:focus {
  background: #43A047;}
.form .message {
  margin: 15px 0 0;
  color: #b3b3b3;
  font-size: 12px;}
body {
  background: #000;
  background: -webkit-linear-gradient(right, #000, #000);
  background: -moz-linear-gradient(right, #000, #000);
  background: -o-linear-gradient(right, #000, #000);
  background: linear-gradient(to left, #000, #000);
  font-family: 'Roboto', sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;}
</style>
<script>
function loadWifiList() {
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
      var list = JSON.parse(this.responseText);
      var select = document.getElementById('name');
      select.innerHTML = '';
      for (var i = 0; i < list.length; i++) {
        var opt = document.createElement('option');
        opt.value = list[i];
        opt.innerHTML = list[i];
        select.appendChild(opt);
      }
    }
  };
  xhttp.open('GET', '/scan', true);
  xhttp.send();
}
function sendSetWifi() {
  var name = document.getElementById('name').value;
  var pass = document.getElementById('pass').value;
  if(name == ''){window.alert('请输入正确的WIFI名称!!!');return false;}
  if(pass == ''){if(!confirm('WIFI密码未输入,如果连接的WIFI没有密码请点击确定,否则点击取消继续输入密码,确定要继续吗?')){return false;}}
  var xhttp = new XMLHttpRequest();
  xhttp.onreadystatechange = function() {
    if (this.readyState == 4 && this.status == 200) {
    if(this.responseText == 'OK'){window.alert('网络配置成功,等待开机卡蓝灯亮起.');}else{window.alert('网络配置失败,保存WIFI连接信息,遇到未知错误.');}
    }
  };
  xhttp.open('post', '/?ssid=' + name + '&password=' + pass, true);
  xhttp.send();
}
</script>
</head>
<body onload='loadWifiList();'>
<div class='login-page'>
    <div class='form'>
  <p class='message'><span style='color:black'>【WIFI WEB配网】- 连接2.4G_WiFi</span></p>
  <p class='message'><span style='color:red'>扫描需要约5秒，扫描完成后选择自己的WiFi</span></p>
  <select id='name' name='ssid'></select>
  <input id='pass' name='password' placeholder='WIFI 密码'>
  <button onclick='javascript:sendSetWifi();'>连接 WIFI</button>
  <p class='message'><span style='color:black'>如果连接的 WIFI 无密码, 请留空即可</span></p>
  <p class='message'><span style='color:black'>WiFi名称/密码不能含有+#&这几个特殊符号</span></p>
  <p class='message'></p>
  <button style='background-color:#D3D3D3;color:black;' onclick='location.reload();'>重新扫描</button>
</div></div>
</body>
</html>
)rawliteral";

/* ===== 2. 电源控制页面 ===== */
static const char PAGE_INDEX[] PROGMEM = R"rawliteral(<!DOCTYPE html>
<html lang='zh-CN'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width,initial-scale=1,user-scalable=no'>
<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;padding:26px 18px 18px;background:#000;font-family:-apple-system,'Segoe UI',Roboto,'Microsoft YaHei',sans-serif;color:#fff}
.card{max-width:420px;margin:0 auto 16px;background:#fff;color:#222;border-radius:14px;padding:18px;box-shadow:0 6px 18px rgba(0,0,0,.5)}
.state{display:flex;align-items:center;justify-content:center;gap:10px;font-size:22px;font-weight:600;padding:14px 0}
.dot{width:14px;height:14px;border-radius:50%;background:#bbb;box-shadow:0 0 0 4px rgba(0,0,0,.05)}
.dot.on{background:#22c55e;box-shadow:0 0 0 4px rgba(34,197,94,.2)}
.dot.off{background:#ef4444;box-shadow:0 0 0 4px rgba(239,68,68,.2)}
.dot.wait{background:#f59e0b;box-shadow:0 0 0 4px rgba(245,158,11,.2)}
.meta{font-size:12px;color:#666;text-align:center;line-height:1.7}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
button{font-family:inherit;font-size:16px;font-weight:600;border:0;border-radius:12px;padding:16px 8px;color:#fff;cursor:pointer;transition:.15s}
button:active{transform:scale(.95)}
button.busy{opacity:.7}
.b-on{background:#22c55e;grid-column:1/3}
.b-off{background:#ef4444}
.b-rst{background:#f59e0b}
.b-ref{background:#64748b;grid-column:1/3;font-size:14px;padding:12px 8px}
.api{font-family:Consolas,Menlo,monospace;font-size:12px;background:#f4f6f8;border-radius:8px;padding:10px;line-height:1.9;word-break:break-all}
.api b{color:#156dc7}
a{color:#156dc7}
#toast{position:fixed;left:50%;bottom:34px;transform:translateX(-50%);background:rgba(0,0,0,.82);color:#fff;padding:11px 18px;border-radius:10px;font-size:14px;opacity:0;transition:.25s;pointer-events:none;z-index:9}
#toast.show{opacity:1}
</style>
</head>
<body>

<div class='card'>
  <div class='state'><span id='dot' class='dot'></span><span id='stateText'>读取中…</span></div>
  <div class='meta' id='meta'>—</div>
  <div class='meta' id='last' style='margin-top:8px;color:#999'>—</div>
</div>

<div class='card'>
  <div class='grid'>
    <button class='b-on'  id='bOn'   onclick="cmd('on')">开 机</button>
    <button class='b-off' id='bOff'  onclick="cmd('off')">关 机</button>
    <button class='b-rst' id='bRst'  onclick="cmd('restart')">重 启</button>
    <button class='b-ref' id='bRef'  onclick="refresh()">刷新状态</button>
  </div>
  <div class='meta' style='margin-top:12px'>状态每 2 秒自动刷新，无需手动刷新页面</div>
  <div class='meta'>关机 = 长按电源键 8 秒强制断电；重启 = 触发主板 RESET</div>
</div>

<div class='card'>
  <div style='font-size:13px;font-weight:600;margin-bottom:8px'>API（GET 一键命令）</div>
  <div class='api'>
    <b>/api?cmd=on</b>　开机<br>
    <b>/api?cmd=off</b>　关机<br>
    <b>/api?cmd=restart</b>　重启<br>
    <b>/api?cmd=status</b>　电源状态(JSON)<br>
    等价写法：<b>/api/on</b> <b>/api/off</b> <b>/api/restart</b> <b>/api/status</b>
  </div>
  <div class='meta' style='margin-top:12px'><a href='/config'>重新配置 WiFi</a> ｜ <a href='/update'>局域网刷机</a> ｜ <a href='/api/status'>状态 JSON</a></div>
</div>

<div id='toast'></div>

<script>
var first=true, lastMsg=null, busy=false;
function toast(t){var e=document.getElementById('toast');e.textContent=t;e.className='show';clearTimeout(e._t);e._t=setTimeout(function(){e.className='';},2600);}
/* 带超时的 fetch：避免设备忙时请求一直挂着 */
function fetchT(url,ms){
  return new Promise(function(res,rej){
    var ctl=(typeof AbortController!=='undefined')?new AbortController():null;
    var done=false;
    var t=setTimeout(function(){ if(!done){done=true; if(ctl)ctl.abort(); rej(new Error('timeout'));} },ms);
    fetch(url,{cache:'no-store',signal:ctl?ctl.signal:undefined}).then(function(r){
      if(done) return; done=true; clearTimeout(t); res(r);
    }).catch(function(e){ if(done) return; done=true; clearTimeout(t); rej(e); });
  });
}
function paint(d){
  busy=!!d.busy;
  var dot=document.getElementById('dot');
  dot.className='dot '+(busy?'wait':(d.power?'on':'off'));
  var nm=(d.cmd===1?'开机':(d.cmd===2?'关机':(d.cmd===3?'重启':'')));
  document.getElementById('stateText').textContent = busy
      ? ('执行中… ' + nm)
      : (d.power?'电源已开启':'电源已关闭');
  document.getElementById('meta').textContent='GPIO14='+d.state+'　GPIO4='+d.sense
      +'　IP '+d.ip+'　RSSI '+d.rssi+'dBm　运行 '+d.uptime+'s　'+d.version;
  document.getElementById('last').textContent='最近指令：'+(d.last||'—')+'　（累计已执行 '+d.cmds+' 条）';
  /* 按钮永不置灰，只加一个淡色提示 */
  ['bOn','bOff','bRst'].forEach(function(id){
    var el=document.getElementById(id);
    if(busy) el.classList.add('busy'); else el.classList.remove('busy');
  });
  /* 首次加载不弹提示；之后只有「最近指令」真的变了才弹，避免刷新页面误以为重发命令 */
  if(!first && d.last && d.last!==lastMsg) toast(d.last);
  lastMsg=d.last;
  first=false;
}
function refresh(){
  fetchT('/api/status?t='+Date.now(),4000).then(function(r){return r.json();})
    .then(paint)
    .catch(function(){ document.getElementById('stateText').textContent='连接失败（自动重试中）'; });
}
function cmd(c){
  toast('已下发：'+c);
  fetchT('/api?cmd='+c+'&t='+Date.now(),8000).then(function(r){return r.json();})
    .then(function(d){ toast(d.msg||('已下发：'+c)); refresh(); })
    .catch(function(){ toast('下发失败，请重试'); });
}
refresh();
setInterval(refresh,2000);
</script>
</body>
</html>
)rawliteral";

/* ===== 3. 局域网刷机页面 ===== */
static const char PAGE_UPDATE[] PROGMEM = R"rawliteral(<!DOCTYPE html>
<html lang='zh-CN'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width,initial-scale=1,user-scalable=no'>
<title>ES12F 局域网刷机</title>
<style>
*{box-sizing:border-box}
body{margin:0;padding:18px;background:#000;font-family:-apple-system,'Segoe UI',Roboto,'Microsoft YaHei',sans-serif;color:#fff}
h1{font-size:19px;text-align:center;margin:0 0 4px}
.sub{text-align:center;font-size:12px;color:#d8e8ff;margin:0 0 18px}
.card{max-width:460px;margin:0 auto 16px;background:#fff;color:#222;border-radius:14px;padding:18px;box-shadow:0 6px 18px rgba(0,0,0,.18)}
label{display:block;font-size:13px;font-weight:600;margin:0 0 8px}
input[type=file]{width:100%;font-size:13px;padding:12px;background:#f4f6f8;border:1px dashed #b9c4cf;border-radius:10px}
button{width:100%;margin-top:14px;font-family:inherit;font-size:16px;font-weight:600;border:0;border-radius:12px;padding:15px;color:#fff;background:#ef4444;cursor:pointer}
button:disabled{opacity:.45}
.ok{background:#22c55e}
.note{font-size:12px;color:#666;line-height:1.8;margin-top:14px}
.warn{background:#fff7ed;border-left:4px solid #f59e0b;padding:10px 12px;border-radius:8px;font-size:12px;color:#7c2d12;line-height:1.8;margin-top:12px}
#s{margin-top:12px;font-size:13px;color:#156dc7;min-height:20px;word-break:break-all}
a{color:#156dc7}
.foot{text-align:center;font-size:12px;color:#d8e8ff;padding-bottom:20px}
</style>
</head>
<body>
<h1>ES12F 局域网刷机</h1>
<p class='sub'>仅接受 10.0.0.0/8 · 172.16.0.0/12 · 192.168.0.0/16 · 127.0.0.0/8 的请求</p>

<div class='card'>
  <label>选择固件文件</label>
  <input id='f' type='file' accept='.bin,application/octet-stream'>
  <button id='b' onclick='go()'>开始刷机</button>
  <div id='s'></div>
  <div class='warn'>
    · 刷机过程中<b>不要断电</b>，约 10~20 秒<br>
    · 新固件会先暂存，再由引导程序拷回 0x0，<b>WiFi 配置不会被清掉</b><br>
    · 设备不会主动连接任何外部服务器，固件只由你的浏览器推送
  </div>
  <div class='note'><a href='/'>返回电源控制页</a></div>
</div>
<div class='foot'>固件 ES12F-LOCAL · 刷机后自动重启</div>

<script>
function go(){
  var f=document.getElementById('f');
  var s=document.getElementById('s');
  var b=document.getElementById('b');
  if(!f.files||!f.files.length){alert('请先选择 .bin 固件文件');return;}
  var fd=new FormData();
  fd.append('firmware',f.files[0],f.files[0].name);
  b.disabled=true;b.textContent='刷机中，请勿断电…';
  s.textContent='正在上传 '+f.files[0].name+' ('+Math.round(f.files[0].size/1024)+' KB) …';
  var x=new XMLHttpRequest();
  x.open('POST','/update'+location.search,true);
  x.upload.onprogress=function(e){
    if(e.lengthComputable){s.textContent='上传中 '+Math.round(e.loaded*100/e.total)+'%';}
  };
  x.onload=function(){
    s.textContent=x.responseText;
    if(x.status==200&&x.responseText.indexOf('OK')===0){
      b.textContent='刷机成功，设备重启中';
      b.className='ok';
      s.textContent='刷机成功！设备正在重启，约 10 秒后访问 / 查看新固件。';
    }else{
      b.disabled=false;b.textContent='重试';
    }
  };
  x.onerror=function(){s.textContent='上传失败（连接中断）';b.disabled=false;b.textContent='重试';};
  x.send(fd);
}
</script>
</body>
</html>
)rawliteral";

#endif /* ES12F_PAGES_H */
