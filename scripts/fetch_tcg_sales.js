// Refresh data/tcg_sealed_products.psv and data/tcg_sealed_sales.psv.
//
// TCGplayer has no public API for completed sales, but its own site shows the 5 most recent completed sales
// for any product. This snippet reads them the same way the site does. It must run in a browser tab that is
// open on https://www.tcgplayer.com (paste it into the DevTools console). It downloads two pipe-separated files.
//
// What you get per box product: the 5 most recent completed sales (date, price, shipping, quantity, condition),
// plus the product's market price and lowest listing for cross-checking. The model uses the median of the 5 sales.
//
// Be polite: the snippet sleeps between requests. Do not loop it.

(async () => {
  const SETS = [['fra','Reality Fracture'],['sos','Secrets of Strixhaven'],['hob','The Hobbit'],['ecl','Lorwyn Eclipsed'],['tla','Avatar: The Last Airbender'],
    ['spm',"Marvel's Spider-Man"],['eoe','Edge of Eternities'],['fin','FINAL FANTASY'],['tdm','Tarkir: Dragonstorm'],['dft','Aetherdrift'],['fdn','Foundations'],
    ['dsk','Duskmourn: House of Horror'],['blb','Bloomburrow'],['mh3','Modern Horizons 3'],['otj','Outlaws of Thunder Junction'],['mkm','Murders at Karlov Manor'],
    ['lci','The Lost Caverns of Ixalan'],['woe','Wilds of Eldraine'],['ltr','Universes Beyond: The Lord of the Rings: Tales of Middle-earth'],['mom','March of the Machine'],
    ['one','Phyrexia: All Will Be One'],['bro',"The Brothers' War"],['dmu','Dominaria United'],['snc','Streets of New Capenna'],['neo','Kamigawa: Neon Dynasty'],
    ['vow','Innistrad: Crimson Vow'],['mid','Innistrad: Midnight Hunt'],['afr','Adventures in the Forgotten Realms'],['stx','Strixhaven: School of Mages'],['khm','Kaldheim'],
    ['znr','Zendikar Rising'],['m21','Core Set 2021'],['iko','Ikoria: Lair of Behemoths'],['thb','Theros Beyond Death'],['eld','Throne of Eldraine'],['m20','Core Set 2020'],
    ['war','War of the Spark'],['rna','Ravnica Allegiance'],['grn','Guilds of Ravnica'],['m19','Core Set 2019'],['dom','Dominaria'],['rix','Rivals of Ixalan'],['xln','Ixalan'],
    ['hou','Hour of Devastation'],['akh','Amonkhet'],['aer','Aether Revolt'],['kld','Kaladesh'],['emn','Eldritch Moon'],['soi','Shadows over Innistrad'],
    ['tmt','Teenage Mutant Ninja Turtles'],['mar','Marvel Super Heroes']];
  const body = {algorithm:'sales_synonym_v2', from:0, size:50, filters:{term:{productLineName:['magic'], productTypeName:['Sealed Products']}, range:{}, match:{}},
    listingSearch:{context:{cart:{}}, filters:{term:{sellerStatus:'Live', channelId:0}, range:{quantity:{gte:1}}, exclude:{channelExclusion:0}}},
    context:{cart:{}, shippingCountry:'US', userProfile:{}}, settings:{useFuzzySearch:true, didYouMean:{}}, sort:{}};
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const dl = (name, text) => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], {type:'text/plain'})); a.download = name; document.body.appendChild(a); a.click(); };
  const prod = [], sales = [];
  for (const [code, name] of SETS) {
    const r = await fetch('https://mp-search-api.tcgplayer.com/v1/search/request?q=' + encodeURIComponent(name + ' booster') + '&isList=false',
      {method:'POST', headers:{'content-type':'application/json'}, body: JSON.stringify(body)});
    const j = await r.json(); const list = j.results?.[0]?.results || [];
    const keep = list.filter(p => p.setName === name && /(Booster Box|Booster Display|Booster Pack)$/.test(p.productName) && !/Case|Omega|Theme|Jumpstart|Arena|Sleeved/.test(p.productName));
    for (const p of keep) {
      prod.push([code, name, p.productId, p.productName, p.marketPrice ?? '', p.lowestPrice ?? '', p.medianPrice ?? ''].join('|'));
      if (/Pack$/.test(p.productName)) continue;
      const s = await fetch(`https://mpapi.tcgplayer.com/v2/product/${p.productId}/latestsales`, {method:'POST', headers:{'content-type':'application/json'},
        body: JSON.stringify({listingType:'All', limit:25, offset:0, time:Date.now()})});
      if (s.ok) { const sj = await s.json(); for (const d of (sj.data || [])) sales.push([code, p.productId, p.productName, d.orderDate.slice(0,10), d.purchasePrice, d.shippingPrice, d.quantity, d.condition, d.language].join('|')); }
      await sleep(300);
    }
    await sleep(400);
  }
  dl('tcg_sealed_products.psv', prod.join('\n')); await sleep(500); dl('tcg_sealed_sales.psv', sales.join('\n'));
  console.log('done', prod.length, 'products', sales.length, 'sales');
})();
