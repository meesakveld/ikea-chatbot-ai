import { QueryKey } from '@tanstack/react-query';

export function createQueryKey(parts: (string | number)[]): QueryKey {
    const queryKey: string[] = [];

    queryKey.push(...parts.map((part) => (typeof part === 'string' ? part : JSON.stringify(part))));

    return queryKey as unknown as QueryKey;
}
