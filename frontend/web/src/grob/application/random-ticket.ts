function randomBelow(limit: number): number {
  const ceiling = Math.floor(0x100000000 / limit) * limit;
  const buffer = new Uint32Array(1);
  do crypto.getRandomValues(buffer); while (buffer[0] >= ceiling);
  return buffer[0] % limit;
}

export function createRandomCombination(max: number, count: number): number[] {
  const pool = Array.from({ length: max }, (_, index) => index + 1);
  for (let index = pool.length - 1; index > 0; index--) {
    const swap = randomBelow(index + 1);
    [pool[index], pool[swap]] = [pool[swap], pool[index]];
  }
  return pool.slice(0, count).sort((a, b) => a - b);
}

export function createRandomTickets(quantity: 1 | 5 | 25, max: number, count: number) {
  return Array.from({ length: quantity }, () => createRandomCombination(max, count));
}

