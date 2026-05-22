// —— Modules ——
import {
    useQuery,
    useQueryClient,
    type QueryKey,
    type QueryFunction,
    type UseQueryResult,
    type UndefinedInitialDataOptions,
} from '@tanstack/react-query';

// —— Core ——
import { isFunction } from '@core/utils/isFunction';

type UseCreateQueryProps<TQueryFnData, TError = Error, TData = TQueryFnData, TQueryKey extends QueryKey = QueryKey> = {
    queryKey: TQueryKey | (() => TQueryKey);
    queryFn: QueryFunction<TQueryFnData, TQueryKey>;
} & Omit<UndefinedInitialDataOptions<TQueryFnData, TError, TData, TQueryKey>, 'queryKey' | 'queryFn'>;

type UseCreateQueryResult<TData, TError> = UseQueryResult<TData, TError> & {
    refresh: () => void;
    clear: () => void;
};

function useCreateQuery<TQueryFnData, TError = Error, TData = TQueryFnData, TQueryKey extends QueryKey = QueryKey>({
    queryKey,
    queryFn,
    ...options
}: UseCreateQueryProps<TQueryFnData, TError, TData, TQueryKey>): UseCreateQueryResult<TData, TError> {
    const finalKey = isFunction(queryKey) ? queryKey() : queryKey;
    const queryClient = useQueryClient();

    const queryResult = useQuery<TQueryFnData, TError, TData, TQueryKey>({
        queryKey: finalKey,
        queryFn,
        ...options,
    });

    const refresh = () => {
        queryClient.invalidateQueries({ queryKey: finalKey });
    };

    const clear = () => {
        queryClient.removeQueries({ queryKey: finalKey });
    };

    return {
        ...queryResult,
        refresh,
        clear,
    };
}

export default useCreateQuery;
