from kombu import Exchange, Queue

task_exchange = Exchange('tasks', type='direct')
task_queues = [Queue('posts', task_exchange, routing_key='posts')]
