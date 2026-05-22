// —— Modules ——
import {
    useMutation,
    useQueryClient,
    type UseMutationOptions,
    type MutationKey,
    type QueryKey,
} from '@tanstack/react-query';

// —— Core ——
import { isFunction } from '@core/utils/isFunction';

// Helper type om return type van Promise van mutationFn te extraheren
type AwaitedReturnType<T> = T extends (...args: any[]) => Promise<infer R> ? R : unknown;

type UseCreateMutationProps<TData, TError, TVariables, TContext> = {
    mutationKey: MutationKey;
    mutationFn: (variables: TVariables) => Promise<TData>;
    onSuccessInvalidateKeys?: QueryKey[];
    onSuccess?: UseMutationOptions<TData, TError, TVariables, TContext>['onSuccess'];
} & Omit<UseMutationOptions<TData, TError, TVariables, TContext>, 'mutationKey' | 'mutationFn' | 'onSuccess'>;

function useCreateMutation<
    TVariables = void,
    TError = Error,
    TContext = unknown,
    TMutationFn extends (variables: TVariables) => Promise<any> = (variables: TVariables) => Promise<any>,
>({
    mutationKey,
    mutationFn,
    onSuccessInvalidateKeys,
    onSuccess,
    ...options
}: UseCreateMutationProps<AwaitedReturnType<TMutationFn>, TError, TVariables, TContext>) {
    const queryClient = useQueryClient();

    return useMutation<AwaitedReturnType<TMutationFn>, TError, TVariables, TContext>({
        mutationKey,
        mutationFn,
        onSuccess: async (data, variables, context) => {
            if (isFunction(onSuccess)) {
                await onSuccess(data, variables, context);
            }

            if (onSuccessInvalidateKeys?.length) {
                onSuccessInvalidateKeys.forEach((key) => {
                    queryClient.invalidateQueries({ queryKey: key });
                });
            }
        },
        ...options,
    });
}

export type Options = Omit<Partial<Parameters<typeof useCreateMutation>[0]>, 'mutationFn' | 'mutationKey'>;

export default useCreateMutation;
