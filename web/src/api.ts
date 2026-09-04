export type Row = Record<string, string>;
export type Summary = { as_of:string; source_label:string; coverage_start:string; coverage_end:string; index_code:string; metrics:Record<string,number>; caveats:string[] };
export async function csv(path:string):Promise<Row[]> { const response=await fetch(path); if(!response.ok) throw new Error(`${path}（${response.status}）`); const text=await response.text(); const [header,...lines]=text.trim().split(/\r?\n/); return lines.map(line=>{const cells=line.split(",");return Object.fromEntries(header.split(",").map((key,i)=>[key,cells[i]??""]))}); }
export async function json<T>(path:string):Promise<T> { const response=await fetch(path); if(!response.ok) throw new Error(`${path}（${response.status}）`); return response.json() as Promise<T>; }
