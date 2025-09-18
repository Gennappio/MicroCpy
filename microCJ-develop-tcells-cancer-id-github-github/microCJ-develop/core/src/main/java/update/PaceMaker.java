/*
Copyright 2019 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package update;

import core.World;
import org.tinylog.Logger;
import utils.Listener;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class PaceMaker {
	public static final int SNAPSHOT_EXTRA = 50; //decided by trial and error
	private static final int THREAD_POOL_SIZE = 1; //right now only one clock task will be spawned at the same time.
	private final World world;
	private long interval;
	private int step = 0;
	private final List<Listener> listeners = new ArrayList<>();
	private ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(THREAD_POOL_SIZE);
	private boolean pauseRequested = false;

	public PaceMaker(World world, long interval) {
		this.world = world;
		this.interval = world.getSnapshots() > 0 ? interval + SNAPSHOT_EXTRA : interval;
	}

	private void startClock(long delay) {
		pauseRequested = false;
		interval = delay;

		Runnable clock = () -> {
			if(!hasPauseBeenRequested()) {
				step++;
				Logger.tag("step").info("World {} - step <{}>]", world.getId(), step);
				world.update();
				Logger.info("World " + world.getId() + " after update " + step);
				for (Listener task : listeners) {
					task.run();
				}
			}
		};
		scheduler.scheduleAtFixedRate(clock, delay, delay, TimeUnit.MILLISECONDS);
	}

	public void startClock() {
		startClock(interval);
	}

	public synchronized void requestPause() {
		pauseRequested = true;
	}

	private synchronized boolean hasPauseBeenRequested() {
		return pauseRequested;
	}

	public void shutdown() {
		scheduler.shutdownNow();
		scheduler = Executors.newScheduledThreadPool(THREAD_POOL_SIZE);
		step = 0;
	}

	public void stop(){
		requestPause();
		scheduler.shutdown();
	}

	/**
	 * Adds a listener to the step counter. Whenever a new step is executed, the given task will be executed as well.
	 * @param task the task that will be executed every step.
	 */
	public void atEveryStep(Listener task) {
		listeners.add(task);
	}

	public int getStep() {
		return step;
	}
}
