/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package core;

/**
 * Enumeration of all possible cell fates, and the actual implementation of those fates.
 * @author Pedro Victori
 */
public enum Fate {
	//this order is important: if several fates are activated in a synchronous network, the first one in this list is chosen.
	APOPTOSIS((cell, tumor) -> {
		cell.apoptose();
	}),
	NECROSIS((cell, tumor) -> {
		cell.necrotize();

	}),
	GROWTH_ARREST((cell, tumor) -> {
		cell.arrest();
	}),


	ACTINREM((cell, tumor) -> {

	}),
	PICYTOKINES((cell, tumor) -> {

	}),
	SURVIVAL((cell, tumor) -> {

	}),
	AICYTOKINES((cell, tumor) -> {

	}),

	ANERGY((cell, tumor) -> {
		cell.apoptose();
	}),
	PROLIFERATION((cell, tumor) -> {
		tumor.addToProliferationQueue(cell);

	}),



	NO_FATE_REACHED(((cell, tumor) -> {})),


	;


	private final FateExecution executionRule;

	Fate(FateExecution executionRule) {
		this.executionRule = executionRule;
	}

	FateExecution getExecutionRule() {
		return executionRule;
	}


	@Override
	public String toString() {
		return name().toLowerCase();
	}
}
