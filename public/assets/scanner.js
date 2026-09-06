(function(){
  const status=document.querySelector('[data-camera-status]');
  const video=document.querySelector('video');
  const form=document.querySelector('[data-manual-form]');
  const input=document.querySelector('[data-manual-input]');
  const error=document.querySelector('[data-manual-error]');
  let controls=null,done=false;

  function validGTIN(code){
    if(!/^\d+$/.test(code)||![8,12,13].includes(code.length))return false;
    const digits=code.split('').map(Number);let sum=0;
    for(let i=digits.length-2,pos=0;i>=0;i--,pos++)sum+=digits[i]*(pos%2===0?3:1);
    return (10-(sum%10))%10===digits[digits.length-1];
  }
  function go(code){
    if(done)return;done=true;controls?.stop?.();if(navigator.vibrate)navigator.vibrate(70);
    status.textContent='嗶！找到條碼 '+code;
    setTimeout(()=>location.href='/lookup/?barcode='+encodeURIComponent(code),220);
  }
  form?.addEventListener('submit',e=>{
    e.preventDefault();error.textContent='';const c=(input.value||'').replace(/\D/g,'');
    if(!validGTIN(c)){error.textContent='請輸入有效的 8、12 或 13 碼商品條碼';return}
    go(c);
  });
  async function start(){
    try{
      if(!window.ZXingBrowser?.BrowserMultiFormatReader)throw new Error('scanner library unavailable');
      const reader=new ZXingBrowser.BrowserMultiFormatReader(undefined,{delayBetweenScanAttempts:120});
      controls=await reader.decodeFromConstraints({video:{facingMode:{ideal:'environment'},width:{ideal:1280},height:{ideal:720}}},video,(result)=>{
        if(!result)return;const code=result.getText().replace(/\D/g,'');
        if(validGTIN(code))go(code);
      });
      status.textContent='相機已開啟，把商品條碼完整放進框內';
    }catch(e){console.error(e);status.textContent='相機無法啟動，請確認 Safari/瀏覽器相機權限，或用下方手動輸入。'}
  }
  addEventListener('pagehide',()=>controls?.stop?.());start();
})();
