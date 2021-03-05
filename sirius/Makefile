default:
	rm -rf .jupiter
	cp -r ../jupiter .jupiter
	docker build -f docker/Dockerfile -t sirius .
publish: default
	docker tag sirius:latest 805908283827.dkr.ecr.us-west-2.amazonaws.com/sirius:latest
	docker push 805908283827.dkr.ecr.us-west-2.amazonaws.com/sirius:latest
