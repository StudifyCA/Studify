// Minimal service worker: makes the app installable and lets it open offline.
// Network first (you always get the newest app when online), cache as backup.
var CACHE='studyos-v5';
self.addEventListener('install',function(e){self.skipWaiting();});
self.addEventListener('activate',function(e){e.waitUntil(caches.keys().then(function(ks){return Promise.all(ks.filter(function(k){return k!==CACHE;}).map(function(k){return caches.delete(k);}));}).then(function(){return self.clients.claim();}));});
self.addEventListener('fetch',function(e){
  var r=e.request;
  var u=new URL(r.url),cdn=(u.hostname==='cdn.jsdelivr.net'&&u.pathname.indexOf('/npm/@supabase/supabase-js')===0);
  if(r.method!=='GET'||(u.origin!==self.location.origin&&!cdn))return; // never touch Supabase API calls; only the app and its cloud library are cached
  e.respondWith(fetch(r,cdn?undefined:{cache:'no-cache'}).then(function(res){
    var copy=res.clone();caches.open(CACHE).then(function(c){c.put(r,copy);});return res;
  }).catch(function(){return caches.match(r).then(function(m){return m||caches.match('./');});}));
});

// Push notifications (daily reminder, partner nudges)
self.addEventListener('push',function(e){
  var d={};try{d=e.data?e.data.json():{};}catch(x){}
  e.waitUntil(self.registration.showNotification(d.title||'CA StudyOS',{body:d.body||'',icon:'icon-192.png',badge:'icon-192.png',data:{url:d.url||'./'},tag:'studyos'}));
});
self.addEventListener('notificationclick',function(e){
  e.notification.close();
  e.waitUntil(self.clients.matchAll({type:'window',includeUncontrolled:true}).then(function(cs){
    for(var i=0;i<cs.length;i++){if('focus' in cs[i])return cs[i].focus();}
    return self.clients.openWindow('./');
  }));
});
