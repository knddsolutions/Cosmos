for f in ./*.yaml; do
    kubectl apply -f $f
done
