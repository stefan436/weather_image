export function getStationTime(dateInput, timeZoneId) {
  const formatter = new Intl.DateTimeFormat('de-DE', {
    timeZone: timeZoneId,
    year: 'numeric', month: 'numeric', day: 'numeric',
    hour: 'numeric', minute: 'numeric', second: 'numeric',
    hour12: false
  });
  
  const d = new Date(dateInput);
  const parts = formatter.formatToParts(d);
  
  const getP = (type) => parseInt(parts.find(p => p.type === type).value, 10);
  
  const year = getP('year');
  const month = getP('month');
  const day = getP('day');
  const hour = getP('hour');
  
  const pad = (n) => String(n).padStart(2, '0');
  
  return {
    d, 
    year, month, day, hour,
    dayIso: `${year}-${pad(month)}-${pad(day)}`, 
    plotlyString: `${year}-${pad(month)}-${pad(day)} ${pad(hour)}:00:00`
  };
}