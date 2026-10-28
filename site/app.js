/* shared: background layers, status, version list */
(function(){
  var REPO="pxdns/autopatcherbuild";
  var VERSIONS=[
    {id:"26.2",note:"First target; the patcher package builds from the private repo."},
    {id:"26.3",note:"In progress: base patches are being re-pointed at 26.3."},
    {id:"1.16.5",note:"In progress: patcher being rebuilt from the existing 1.16.5 port."},
    {id:"1.14",note:"In progress: patcher being reverse-engineered from the existing 1.14 workspace."},
    {id:"1.12",note:"In progress: patcher being reverse-engineered from the existing 1.12 source."}
  ];
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]});}
  /* version list + status (only on pages that have the containers) */
  var list=document.getElementById("list"), limit=+(list&&list.getAttribute("data-limit"))||0;
  function render(releases){
    if(!list) return;
    var latest={};
    (releases||[]).forEach(function(r){
      var m=/^(.+)-r\d+$/.exec(r.tag_name||""); if(!m||latest[m[1]]||r.draft) return;
      var jar=(r.assets||[]).filter(function(a){return /\.jar$/.test(a.name);})[0];
      if(jar) latest[m[1]]={url:jar.browser_download_url,name:jar.name,size:jar.size,when:r.published_at,tag:r.tag_name};
    });
    var vs=limit?VERSIONS.slice(0,limit):VERSIONS;
    list.innerHTML='<table class="vt"><thead><tr><th>Version</th><th>Status</th><th>Details</th><th></th></tr></thead><tbody>'+vs.map(function(v){
      var rel=latest[v.id];
      var act=rel?'<a class="btn" href="'+esc(rel.url)+'">Download</a>':'<a class="btn off">Not available</a>';
      var sub=rel?'<span class="meta">'+esc(rel.name)+" &middot; "+(rel.size>=1048576?(rel.size/1048576).toFixed(1)+" MB":Math.max(1,Math.round(rel.size/1024))+" KB")+" &middot; "+esc(rel.tag)+" &middot; "+new Date(rel.when).toLocaleDateString()+"</span>":'<span class="note">'+esc(v.note)+"</span>";
      return '<tr><td class="ver">Minecraft '+esc(v.id)+'</td><td><span class="tag '+(rel?"ok":"wip")+'">'+(rel?"ready":"in progress")+'</span></td><td>'+sub+'</td><td class="act">'+act+'</td></tr>';
    }).join("")+"</tbody></table>";
  }
  function status(runs){
    var dot=document.getElementById("dot"),t=document.getElementById("status-text"); if(!dot) return;
    var r=(runs||[])[0];
    if(!r){t.textContent="No builds have run yet.";return;}
    var when=new Date(r.created_at).toLocaleString();
    if(r.status!=="completed"){dot.className="dot run";t.textContent="Building now (started "+when+"). This page updates itself.";return;}
    if(r.conclusion==="success"){dot.className="dot ok";t.textContent="Last build succeeded ("+when+").";}
    else{dot.className="dot bad";t.textContent="Last build "+(r.conclusion||"failed")+" ("+when+").";}
  }
  function get(path){return fetch("https://api.github.com/repos/"+REPO+path,{headers:{Accept:"application/vnd.github+json"}}).then(function(r){if(!r.ok)throw new Error(r.status);return r.json();});}
  function refresh(){
    if(list) get("/releases?per_page=30").then(render).catch(function(){render([]);});
    if(document.getElementById("dot")) get("/actions/workflows/build-patcher.yml/runs?per_page=1").then(function(d){status(d.workflow_runs);}).catch(function(){var t=document.getElementById("status-text");if(t)t.textContent="Build status is not available right now.";});
  }
  if(list||document.getElementById("dot")){refresh();setInterval(refresh,60000);}
})();

(function(){
  var b=document.getElementById("theme"); if(!b) return;
  var root=document.documentElement;
  try{var t=localStorage.getItem("theme"); if(t==="light"||t==="dark") root.setAttribute("data-theme",t);}catch(e){}
  function cur(){var t=root.getAttribute("data-theme"); if(t) return t; return window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";}
  function label(){b.textContent=cur()==="dark"?"Light theme":"Dark theme";}
  label();
  b.addEventListener("click",function(){var n=cur()==="dark"?"light":"dark"; root.setAttribute("data-theme",n); try{localStorage.setItem("theme",n);}catch(e){} label();});
})();
