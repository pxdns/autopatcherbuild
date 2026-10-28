/* shared: background layers, status, version list */
(function(){
  var REPO="pxdns/autopatcherbuild";
  var VERSIONS=[
    {id:"26.2",bg:"g26",note:"First target; the patcher package builds from the private repo."},
    {id:"26.3",bg:"g26",note:"In progress: base patches are being re-pointed at 26.3."},
    {id:"1.16.5",bg:"g16",note:"In progress: patcher being rebuilt from the existing 1.16.5 port."},
    {id:"1.14",bg:"1.14",note:"In progress: patcher being reverse-engineered from the existing 1.14 workspace."},
    {id:"1.12",bg:"1.12",note:"In progress: patcher being reverse-engineered from the existing 1.12 source."}
  ];
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]});}
  /* backgrounds */
  var bg=document.querySelector(".bg");
  var layers={};
  if(bg){
    ["1.14","1.12","g26","g16"].forEach(function(k){
      var i=document.createElement("i");
      if(k.charAt(0)==="g") i.className=k; else i.style.backgroundImage='url("img/bg-'+k+'.jpg")';
      bg.appendChild(i); layers[k]=i;
    });
    var def=document.body.getAttribute("data-bg")||"1.14";
    window.setBg=function(k){Object.keys(layers).forEach(function(n){layers[n].classList.toggle("on",n===k);});};
    window.defaultBg=def; setBg(def);
  }
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
    list.innerHTML=vs.map(function(v){
      var rel=latest[v.id];
      var right=rel?'<a class="btn" href="'+esc(rel.url)+'">Download</a>':'<a class="btn off">Not available yet</a>';
      var sub=rel?esc(rel.name)+" &middot; "+(rel.size>=1048576?(rel.size/1048576).toFixed(1)+" MB":Math.max(1,Math.round(rel.size/1024))+" KB")+" &middot; "+esc(rel.tag)+" &middot; "+new Date(rel.when).toLocaleDateString():esc(v.note);
      return '<div class="card glass" data-bg="'+v.bg+'"><div><h3>Minecraft '+esc(v.id)+'<span class="badge '+(rel?"ok":"wip")+'">'+(rel?"ready":"in progress")+'</span></h3><small>'+sub+'</small></div>'+right+'</div>';
    }).join("");
    [].forEach.call(list.querySelectorAll(".card"),function(c){
      c.addEventListener("mouseenter",function(){window.setBg&&setBg(c.getAttribute("data-bg"));});
      c.addEventListener("mouseleave",function(){window.setBg&&setBg(window.defaultBg);});
    });
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
