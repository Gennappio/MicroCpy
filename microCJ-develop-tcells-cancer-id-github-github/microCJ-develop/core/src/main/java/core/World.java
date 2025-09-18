/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package core;

import diffusion.DiffusibleBase;
import diffusion.DiffusionLattice2D;
import diffusion.DiffusionLattice3D;
import diffusion.DiffusionModel;
import geom.threeDim.Point3D;
import graph.Input;
import graph.NetworkType;
import graph.Subpopulation;
import graph.SynchronousBooleanNetwork;
import org.apache.commons.configuration2.HierarchicalConfiguration;
import org.apache.commons.configuration2.tree.ImmutableNode;
import org.tinylog.Logger;
import stats.Stats;
import update.*;
import utils.Listener;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.PriorityBlockingQueue;

import static core.SettingsProvider.SETTINGS_PROVIDER;
import static graph.Subpopulation.*;

/**
 * Class that represents a single world, an instance stores references to all elements of the model,
 * and is responsible for loading the settings file, starting, pausing and finishing the simulation.
 *
 * @author Pedro Victori
 */
public class World extends Identifier {
	private static final String DEFAULT_STATS = "stats";
	private final BlockingQueue<Update<UpdateFlag, Updatable>> updateQueue = new PriorityBlockingQueue<>();
	private final BlockingQueue<Update<UpdateFlag, Updatable>> guiUpdateQueue = new PriorityBlockingQueue<>();
	private final List<Listener> finishListeners = new ArrayList<>();
	private Tumor tumor;
	private DiffusionModel diffusionModel;
	private PaceMaker paceMaker;
	private int stepLimit = -1; //will never be checked if it isn't set to a value above 0, see update method
	private long start;
	private long alreadyElapsed;
	private boolean setupCompleted = false;
	private boolean multipleWorlds;
	private boolean twoDim;
	private Stats stats;
	private String statsTitle;
	private int snapshots = 0; //frequency of snapshots, 0 turns them off.
	private boolean shoving;
	private boolean diffusion;
	private String tag;

	public World() {
		System.setProperty("exp.tag", "gui");
		//System.setProperty("tinylog.configuration", "tinylog_just-timepoints.properties"); //todo remove in published version, comment out as needed for now.
		SETTINGS_PROVIDER.load();
		Logger.tag("setup").info("world initiated");
	}

	/**
	 * Constructor meant to be used by CLIs, since in those cases the settings and the step limit has to be set beforehand, not through a GUI.
	 *
	 * @param settingsFile the name of the XML file that stores the settings
	 * @param stepLimit    the number of steps after which the simulation will stop
	 */
	public World(String settingsFile, Integer stepLimit) {
		this(settingsFile, stepLimit, null);
	}

	/**
	 * Constructor meant to be used by CLIs, since in those cases the settings and the step limit has to be set beforehand, not through a GUI.
	 *
	 * @param settingsFile the name of the XML file that stores the settings
	 * @param stepLimit    the number of steps after which the simulation will stop
	 * @param index        the index of the settings to use under a sensitivity analysis
	 */
	public World(String settingsFile, Integer stepLimit, Integer index) {
		if(index == null){
			SETTINGS_PROVIDER.load(settingsFile, true); //todo to experiment
		} else {
			SETTINGS_PROVIDER.load(settingsFile, true, index);
		}

		this.stepLimit = stepLimit;
	}

	/**
	 * Creates new Tumor and DiffusionModel instances using parameters from settings file, ready to start the simulation.
	 */
	public void setup(boolean multipleWorlds, boolean twoDim) {
		this.multipleWorlds = multipleWorlds;
		this.twoDim = twoDim;
		UpdateCollector updateCollector = this::addToUpdateQueues; //updateCollector to be added to tumour (for detecting new cells) and to all cells (for detecting apoptosis and necrosis)
		var settings = SETTINGS_PROVIDER;
		if (!multipleWorlds) snapshots = settings.getGeneralInt("snapshots");
		NetworkType networkType = NetworkType.valueOf(settings.getGeneralString("network").strip().toUpperCase());

		//enforcing setting rules
		boolean probabilistic = networkType.equals(NetworkType.PROB);
		boolean parseData = settings.getBoolean("gene-status-data.parse");
		boolean spatial = settings.getBoolean("gene-status-data.spatial");

		boolean notProbabilisticAndParse = !probabilistic && parseData;
		boolean spatialAndNot2D = spatial && !twoDim;
		if(notProbabilisticAndParse) throw new IllegalStateException("If parsing expression data, the probabilistic setting must be true");
		if(spatialAndNot2D) throw new IllegalStateException("Spatial data importing only works in 2D");

		//networks
		SynchronousBooleanNetwork.setDecisionWindow(settings.getGeneralInt("decision-window"));
		Cell.setArrestTime(settings.getGeneralInt("arrest-time"));
		Cell.setNetworkType(networkType);

		try{
			Cell.setInitial(String.valueOf(settings.getGeneralDouble("initial-states")));
		} catch (NumberFormatException nfe){
			Cell.setInitial(settings.getGeneralString("initial-states"));
		}

		if(settings.getSettings().containsKey("fixed-inputs") && settings.getGroupSize("fixed-inputs") > 0){
			for (HierarchicalConfiguration<ImmutableNode> input : settings.getSettings().configurationsAt("fixed-inputs")) {
				String tag = input.getString("input");
				Input.addFixed(tag);
			}
		}

		//tumor and subpopulations
		shoving = settings.getGeneralBoolean("shoving");
		List<Subpopulation> subpopulations;

		if (parseData) {
			int nMutationGroups = settings.getGroupSize("mutations");
			if (nMutationGroups > 0) {
				subpopulations = parseExpressionWithMutations();
			} else {
				subpopulations = parseExpression();
			}
		} else {
			subpopulations = parseMutations();
		}

		tumor = new Tumor(Objects.requireNonNull(subpopulations, "subpopulation importing failed"), Point3D.ZERO, updateCollector, twoDim);
		Logger.tag("setup").info("tumor initiated");

		//diffusion
		diffusion = settings.getGeneralBoolean("diffusion");
		double dv = settings.getGeneralDouble("diffusion-voxel-size");
		if (diffusion) {
			int max = settings.getGeneralInt("diffusion-grid-size");
			var diffusibles = DiffusibleBase.parseDiffusibles(dv * 1E-6); //convert um to meters
			diffusionModel = twoDim ?
					new DiffusionLattice2D(max, dv, diffusibles, tumor.getCellList()) :
					new DiffusionLattice3D(max, dv, diffusibles, tumor.getCellList());
		}
		Logger.tag("setup").info("diffusion model initiated");

		//stats
		statsTitle = settings.getString("stats[@filename]", DEFAULT_STATS);
		stats = new Stats(statsTitle, !multipleWorlds, tag);
		getPaceMaker().atEveryStep(() -> stats.takeMeasures(this, getPaceMaker().getStep())); //adds a listener so that measures are taken at every time point
		if (!multipleWorlds) whenFinished(stats::finish);

		setupCompleted = true;
	}

	/**
	 * Starts/resumes simulation.
	 * Specifically, it tells the PaceMaker instance to keep updating World at every time point.
	 */
	public void start() {
		if (!setupCompleted)
			throw new IllegalStateException("Setup has not been completed. Call setup() before calling this method");
		System.out.println("World " + getId() + " starting.");
		start = System.nanoTime();

		getPaceMaker().startClock();
	}

	/**
	 * Pauses simulation.
	 * Specifically, it tells the pacemaker instance not to update World in subsequent time points.
	 */
	public void pause() {
		alreadyElapsed += System.nanoTime() - start;
		getPaceMaker().requestPause();
	}

	/**
	 * Stops simulation and set a new one up. The new simulation stays stopped until start() is called
	 */
	public void reset() {
		setupCompleted = false;
		getPaceMaker().shutdown(); //the clock will be stopped until next call to start()
		setup(multipleWorlds, twoDim);
	}

	public PaceMaker getPaceMaker() {
		if (paceMaker == null) {
			int interval = SETTINGS_PROVIDER.getGeneralInt("step-delay");
			paceMaker = new PaceMaker(this, interval); //lazy initialization
		}
		return paceMaker;
	}

	public Long getElapsed() {
		return System.nanoTime() - start + alreadyElapsed;
	}

	public Tumor getTumor() {
		return tumor;
	}

	public DiffusionModel getDiffusionModel() {
		return diffusionModel;
	}

	/**
	 * Updates all parts of the simulator:
	 * <p><ul>
	 * <li>Tick all cells in the tumor.
	 * <li>Execute all the updates from the queue.
	 * <li>Update agents in the diffusion model.
	 * <li>Update diffusion model.
	 * </ul><p>
	 */
	public void update() {
		Logger.info("World " + getId() + " starting update");
		tumor.tickAllCells();
		Logger.info("World " + getId() + " cells ticked");
		boolean shovingPending = false;
		while (getRemainingUpdates() > 0) {
			Update<UpdateFlag, Updatable> update = popUpdateFromQueue();
			if (shoving && update.getFlag().equals(UpdateFlag.NEW_CELL))
				shovingPending = true; //we have to shove all cells if at least one was created.
			tumor.executeUpdate(update);
		}
		if (shoving && shovingPending) tumor.shove();
		Logger.info("World " + getId() + " tumor update done");

		//diffusion model update
		if (diffusion) {
			diffusionModel.updateCells(tumor.getCellList());
			Logger.info("World " + getId() + " diffusion agents update done");
			diffusionModel.update(getPaceMaker().getStep()); //diffusion update for next time point tumor update\
			Logger.info("World " + getId() + " diffusion update done");
		}

		if (getPaceMaker().getStep() == stepLimit) { //finishing up
			finish();
		}
	}

	public void finish(){
		System.out.println("World " + getId() + " finishing.");
		for (Listener finishListener : finishListeners) {
			finishListener.run();
		}
		getPaceMaker().stop();
		paceMaker = null;
		System.out.println("World " + getId() + " finished");
	}

	/**
	 * Retrieves and removes the head of the update queue, or returns null if there are not available updates.
	 * The head will be the element with the highest UpdateFlag priority
	 *
	 * @return an Update that has been removed from the head of the update queue or null if no available updates.
	 */
	private Update<UpdateFlag, Updatable> popUpdateFromQueue() {
		return updateQueue.poll();
	}

	/**
	 * Retrieves and removes the head of the GUI update queue, or returns null if there are not available updates.
	 * The head will be the element with the highest UpdateFlag priority
	 *
	 * @return an Update that has been removed from the head of the GUI update queue or null if no available updates.
	 */
	public Update<UpdateFlag, Updatable> popUpdateFromGuiQueue() {
		return guiUpdateQueue.poll();
	}

	/**
	 * Get the number of updates in the GUI UpdateQueue
	 *
	 * @return an int with the number of updates remaining in the UpdateQueue
	 */
	public int getRemainingGuiUpdates() {
		return guiUpdateQueue.size();
	}

	/**
	 * Get the number of updates in the UpdateQueue
	 *
	 * @return an int with the number of updates remaining in the UpdateQueue
	 */
	private int getRemainingUpdates() {
		return updateQueue.size();
	}

	/**
	 * Inserts the specified update into the queues, waiting if necessary for space to become available.
	 *
	 * @param update the update to be added
	 */
	private void addToUpdateQueues(Update<UpdateFlag, Updatable> update) {
		try {
			updateQueue.put(update);
		} catch (InterruptedException e) {
			System.out.println("Interrupted exception when adding element to update queue");
			e.printStackTrace();
		}
		try {
			guiUpdateQueue.put(update);
		} catch (InterruptedException e) {
			System.out.println("Interrupted exception when adding element to GUI update queue");
			e.printStackTrace();
		}
	}

	public List<String> getStatsLines() {
		return stats.getLines();
	}

	public String getStatsTitle() {
		return statsTitle;
	}

	public void whenFinished(Listener listener) {
		finishListeners.add(listener);
	}

	public int getSnapshots() {
		return snapshots;
	}

	public boolean isShovingActive() {
		return shoving;
	}

	public boolean isDiffusionActive() {
		return diffusion;
	}

	public void setTag(String tag) {
		this.tag = tag;
	}

	public boolean isTwoDim() {
		return twoDim;
	}
}

