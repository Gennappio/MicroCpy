/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package graph;

import core.Identifier;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;

/**
 * @author Pedro Victori
 */
public class Input extends Identifier implements Node{
	private int resistanceP = 0;
	private final String tag;
	private boolean active;

	private int resistance = 0;
	private static List<String> fixed = new ArrayList<>();
	private boolean isFixed;

	public Input(String tag) {
		this.tag = tag;
		isFixed = fixed.contains(tag);
		active = isFixed;
	}

	@Override
	public String getTag() {
		return tag;
	}

	@Override
	public void setActive(boolean active) {
		if(!isFixed) {
			this.active = active;
		}
	}

	@Override
	public boolean isActive() {
		var r = ThreadLocalRandom.current();
		if(active && resistance > 0){
			if(resistance < r.nextInt(1000)){
				setActive(false);
			}
		}
		if(active && resistanceP > 0){
			if(resistanceP < r.nextInt(1000)){
				resistance += r.nextInt(100);
				if(resistance > 1000){
					resistance = 1000;
				}
			}
		}
		return active;
	}

	@Override
	public boolean computeState(Map<String, Boolean> values) {
		return active;
	}

	@Override
	public NodeType getNodeType() {
		return NodeType.INPUT;
	}

	@Override
	public String toString() {
		return tag;
	}

	public static void addFixed(String tag){
		fixed.add(tag);
	}

	public void setResistanceP(int resistanceP) {
		this.resistanceP = resistanceP;
	}
}
