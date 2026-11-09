// Follow every API page so client-side search covers the whole catalogue.
export async function loadAllPages<T>(fetchPage: (offset: number, limit: number) => Promise<T[]>): Promise<T[]> {
  const rows: T[] = [];
  const limit = 100;
  for (let offset = 0; ; offset += limit) {
    const page = await fetchPage(offset, limit);
    rows.push(...page);
    if (page.length < limit) return rows;
  }
}
