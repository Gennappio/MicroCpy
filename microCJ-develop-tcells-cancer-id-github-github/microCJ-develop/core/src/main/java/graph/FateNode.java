/*
Copyright 2020 Pedro Victori

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
 */
package graph;

import core.Fate;
import core.Identifier;

import java.util.Map;

/**
 * @author Pedro Victori
 */
public class FateNode extends Identifier implements Node{
	private final String tag;
	private boolean active;
	private Rule rule;
	private Fate fate;

	FateNode(String tag, String rule) {
		this.tag = tag;
		this.rule = Rule.parser(rule);
		this.fate = Fate.valueOf(tag.toUpperCase());
	}

	public Fate getFate() {
		return fate;
	}

	@Override
	public String getTag() {
		return tag;
	}

	@Override
	public void setActive(boolean active) {
		this.active = active;
	}

	@Override
	public boolean isActive() {
		return active;
	}

	@Override
	public boolean computeState(Map<String, Boolean> values) {
		return rule.computeRule(values);
	}


	@Override
	public NodeType getNodeType() {
		return NodeType.FATE;
	}

	@Override
	public String toString() {
		return tag;
	}
}
