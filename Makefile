user=$(shell whoami)
pythonNodeProcesses=$(shell pgrep -u $(user) -f "python3 node.py")
pythonControllerProcesses=$(shell pgrep -u $(user) -f "python3 controller.py")



kill:
ifeq ($(pythonControllerProcesses),)
	@echo "No python3 controller processes running! :)"
else
	@pkill -9 -u $(user) -f "python3 controller.py"
	@echo "Controller Killed."
endif
ifeq ($(pythonNodeProcesses),)
	@echo "No python3 node processes running! :)"
else
	@pkill -9 -u $(user) -f "python3 node.py"
	@echo "Nodes Killed. It was a massacre! :("
endif

case1: kill
	@echo "Starting Controller!"
	@python3 controller.py &
	@sleep 2
	@echo "Starting Nodes!"
	@python3 node.py 4 & 
	@python3 node.py 5 & 
	@python3 node.py 6 & 
	@python3 node.py 9 receiver 0 & 
	@python3 node.py 0 sender "this is node 0 multicast message" & 
	@echo "Run 'make kill' to kill the controller and active nodes. Otherwise, they will end automatically in about 4 minutes or if you start another case."

case2: kill
	@echo "Starting Controller!"
	@python3 controller.py &
	@sleep 2
	@echo "Starting Nodes!"
	@python3 node.py 4 & 
	@python3 node.py 5 & 
	@python3 node.py 9 receiver 0 & 
	@python3 node.py 0 sender "this is node 0 multicast message" & 
	@python3 node.py 8 receiver 0 & 
	@echo "Run 'make kill' to kill the controller and active nodes. Otherwise, they will end automatically in about 4 minutes or if you start another case."

case3: kill

	@python3 controller.py &
	@sleep 2
	@echo "Starting Nodes!"
	@python3 node.py 4 & 
	@python3 node.py 5 & 
	@python3 node.py 9 receiver 0 & 
	@python3 node.py 0 sender "this is node 0 multicast message" & 
	@python3 node.py 3 & 
	@echo "Sleeping... zzZZ (40 sec)"
	@sleep 40 
	-@kill -9 $$(pgrep -u $(user) -f "python3 node.py 3")
	@echo "Killed Node 3 :("
	@echo "Run 'make kill' to kill the controller and active nodes. Otherwise, they will end automatically in about 3 minutes or if you start another case."

case4: kill
	@echo "Starting Controller!"
	@python3 controller.py &
	@sleep 2
	@echo "Starting Nodes!"
	@python3 node.py 4 & 
	@python3 node.py 5 & 
	@python3 node.py 6 & 
	@python3 node.py 9 receiver 0 & 
	@python3 node.py 0 sender "this is node 0 multicast message" & 
	@echo "Sleeping... zzZZ (40 sec)"
	@sleep 40 
	@python3 node.py 1 sender "this is node 1 multicast message" & 
	@echo "Node 1 Started :)"
	@echo "Run 'make kill' to kill the controller and active nodes. Otherwise, they will end automatically in about 3 minutes or if you start another case."

clean: kill
	@echo "Removing pycache..."
	@rm -fr __pycache__
	@echo "Removing input and output directories..."
	@rm -fr input
	@rm -fr output
	@echo "Squeaky Clean! :)"