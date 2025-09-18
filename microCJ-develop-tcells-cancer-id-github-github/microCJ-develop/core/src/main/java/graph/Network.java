/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package graph;

import core.Fate;
import org.jgrapht.Graph;

import java.util.Map;
import java.util.Set;

public interface Network {
	Graph<Node, Edge> getGraph();

	Set<Edge> getEdges();

	Set<Node> getNodes();

	Set<Gene> getGenes();

	Set<Node> getInputs();

	Set<Node> getFates();

	void deactivateInputs();

	boolean isNodeActive(String nodeTag);

	/**
	 * When called, update the whole gene network and return the fate reached.
	 * @return The last Fate to be reached, or NO_FATE_REACHED if none reached
	 */
	Fate update();

	void resetDecisionTimer();

	/**
	 * Return the node with the specified tag
	 * @param tag tag of the node to be found
	 * @return A Node with that tag if found, null otherwise
	 */
	Node findNodeWithTag(String tag);

	Network activateGenes(String initial);

	Network turnGenes(boolean on);

	Network turnNodes(boolean on);

	Network turnInputs(boolean on);

	Network turnFates(boolean on);

	/**
	 * Turn a specific node on or off
	 * @throws IllegalArgumentException if no node found with that tag
	 * @param tag tag of the node to be turned on or off
	 * @param on true for turning it on, false for turning it off
	 * @return the Network with the applied change
	 */
	Network turnNode(String tag, boolean on) throws IllegalArgumentException;

	void applyMutations(Map<String, Mutation> mutations);

	/**
	 * Return a map with all mutations present in genes in this network. This is the method to be used to
	 * copy a cell's mutations because mutations can change during runtime.
	 * @return a map with all mutations present in genes in this network, with the gene tag as key.
	 */
	Map<String, Mutation> gatherMutations();

	/**
	 * Make the network acquire mutations with a given probability.
	 * @param mutationChance
	 * @return true if a mutation has occurred, false otherwise.
	 */
	boolean mutate(double mutationChance);
}
